import json
import logging
from uuid import UUID
from pathlib import Path
from datetime import datetime
from typing import Mapping, Any
from urllib import error, parse, request
from dataclasses import dataclass, field
from uuid import uuid4
from time import sleep
from random import uniform

from mahkrabdtn.client.store.processedmessages import ProcessedMessagesStore
from mahkrabdtn.client.policys import RelayRetryPolicy
from mahkrabdtn.crypto.rsa import RsaEncryption
from mahkrabdtn.protocol.node.registration import NodeRegistration
from mahkrabdtn.client.networking.error import RelayClientError
from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.client.reciepts import MessageSubmissionReceipt
from mahkrabdtn.protocol.
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.client.networking.error import is_retryable_http_error


logger = logging.getLogger(__name__)



def create_node_id(identityPath: str | Path) -> UUID:
    path = Path(identityPath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): return UUID(path.read_text(encoding="utf-8").strip())
    
    nodeID = uuid4()
    path.write_text(str(nodeID), encoding="utf-8")
    
    return nodeID


@dataclass(slots=True)
class RelayNodeClient:
    baseURL: str
    nodeID: UUID
    privateKeyPem: str
    publicKeyPem: str
    processedMessagesStore: ProcessedMessagesStore
    timeout: float = 5.0
    retryPolicy: RelayRetryPolicy = field(default_factory=RelayRetryPolicy)
    
    @classmethod
    def from_identity_path(
        cls, baseURL: str, identityPath: str | Path,
        timeout: float = 5.0,
    ) -> "RelayNodeClient":
        
        pair = RsaEncryption.create_node_key_pair(identityPath)
        
        return cls(
            baseURL=baseURL.rstip("/"),
            nodeID=create_node_id(identityPath),
            privateKeyPem=pair.privateKeyPem,
            publicKeyPem=pair.publicKeyPem,
            processedMessagesStore=ProcessedMessagesStore.from_identity_path(identityPath),
            timeout=timeout
        )
        
    def __post_init__(self) -> None:
        self.baseURL = self.baseURL.rstrip("/")
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        
        if self.timeout <= 0: raise ValueError("timeout must be positive")
        if not isinstance(self.processedMessagesStore, ProcessedMessagesStore): raise TypeError("processedMessageStore must be of type ProcessedMessageType, duh")
        if not isinstance(self.retryPolicy, RelayRetryPolicy): raise TypeError("retryPolicy must be of type RetryPolicy")
        
    def register(self) -> NodeRegistration:
        response = self.send_json_request(
            mathod="POST",
            path="/nodes/register",
            payload={
                "nodeID": str(self.nodeID),
                "publicKey": self.publicKeyPem,
            },
        )
        registration = NodeRegistration.from_dict(response)
        logger.info(
            "client.node.registered",
            extra={
                "nodeID": str(self.nodeID),
                "baseURL": self.baseURL,
                "hasPublicKey": True,
            },
        )
        return registration
    
    def fetch_node_registration(self, nodeID: UUID) -> NodeRegistration:
        response = self.send_json_request(
            method="GET",
            path=f"/nodes/{parse_uuid(nodeID, "nodeID")}",
        )
        return NodeRegistration.from_dict(response)
    
    def create_packet(
        self,
        recipientID: UUID,
        payload: str,
        recipientPublicKey: str,
        expiresAt: datetime | None = None,
        version: str = "1.0",
    ) -> MessagePacket:
        
        ciphertext, encryption = RsaEncryption.encrypt(payload, recipientPublicKey)
        return MessagePacket(
            senderID=self.nodeID,
            recipientID=recipientID,
            payload=ciphertext,
            encryption=encryption,
            expires=expiresAt,
            version=version,
        )        
        
    def send_message(
        self,
        recipientID: UUID,
        payload: str,
        recipientPublicKey: str | None = None,
        expiresAt: datetime | None = None,
        version: str = "1.0",
    ) -> MessageSubmissionReceipt:
        recipientID = parse_uuid(recipientID, "recipientID")
        recipientPublicKey = recipientPublicKey or self.resolve_recipient_public_key(
            recipientID
        )
        packet = self.create_packet(
            recipientID,
            payload,
            recipientPublicKey=recipientPublicKey,
            expiresAt=expiresAt,
            version=version,
        )
        response = self.send_json_request(
            method="POST",
            path="/messages",
            payload=packet.to_dict(),
        )
        receipt = MessageSubmissionReceipt.from_dict(response)
        
        logger.info(
            "client.message.sent",
            extra={
                "nodeID": str(self.nodeID),
                "messageID": str(receipt.messageID),
                "recipientID": str(recipientID),
                "state": receipt.state.value,
            },
        )
        return receipt
    

    def poll_messages(self, timeout: int = 0) -> PollResponse:
        
        
    def send_json_request(
        self, method: str, path: str, 
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        
        requestURL = f"{self.baseURL}{path}"
        requestHeaders = {"Content-Type": "application/json"}
        requestBody = None
        
        if payload is not None: requestBody = json.dumps(payload).encode("utf-8")
        
        for attempt in range(self.retryPolicy.maxAttempts):
            httpRequest = request.Request(
                url=requestURL,
                data=requestBody,
                headers=requestHeaders,
                method=method,
            )
            
            try: 
                responseBody = self.execute_http_request(httpRequest)
                responseBody = json.loads(responseBody)
                
                if not isinstance(responseBody, dict): raise RelayClientError("relay response must be a JSON object, silly internet")
                return responseBody

            except error.HTTPError as e:
                errorBody = e.read().decode("utf-8")
                relayError = RelayClientError(
                    f"{method} {path} failed with {e.code}: {errorBody}"
                )                
                if (
                    not is_retryable_http_error(e)
                    or self.is_last_attempt(attempt)
                ): 
                    logger.warning(
                        "clinet.http_request.failed",
                        extra={
                            "nodeID": str(self.nodeID),
                            "method": method,
                            "path": path,
                            "attempt": attempt + 1,
                            "reason": str(relayError),
                        },
                    )
                    raise relayError from e
                
                logger.info(
                    "client.http_request.retrying",
                    extra={
                        "nodeID": str(self.nodeID),
                        "method": method,
                        "path": path,
                        "attempt": attempt + 1,
                        "reason": f"http_{e.code}",
                    },
                )
            
            except TimeoutError as e:
                relayError = RelayClientError(f"{method} {path} timed out")
                if self.is_last_attempt(attempt):
                    logger.warning(
                        "client.http_request.failed",
                        extra={
                            "nodeID": str(self.nodeID),
                            "method": method,
                            "path": path,
                            "attempt": attempt + 1,
                            "reason": "timeout",
                        },
                    )
                
            except error.URLError as e:
                relayError = RelayClientError(f"{method} {path} failed: {e.reason}")
                if self.is_last_attempt(attempt):
                    logger.warning(
                        "client.http_request.failed",
                        extra={
                            "nodeID": str(self.nodeID),
                            "method": method,
                            "path": path,
                            "attempt": attempt + 1,
                            "reason": str(e.reason),
                        },
                    )
                    raise relayError from e
                logger.info(
                    "client.http_request.retrying",
                    extra={
                        "nodeID": str(self.nodeID),
                        "method": method,
                        "path": path,
                        "attempt": attempt + 1,
                        "reason": str(e.reason),
                    },
                )
                
            self.sleep_retry(attempt)
        
        raise AssertionError("how did we get here?")
            
    def resolve_recipient_public_key(self, recipientID: UUID) -> str:
        registration = self.fetch_node_registration(recipientID)
        if registration.publicKey is None: raise RelayClientError(f"recipient {recipientID} has no registered public key")
        
        return registration.publicKey        
            
    def sleep_retry(self, attempt: int) -> None:
        delay = self.backoff_delay(attempt)
        if delay > 0:
            sleep(delay)
            
    def is_last_attempt(self, attempt: int) -> bool:
        return attempt >= self.retryPolicy.maxAttempts - 1


    def execute_http_request(self, httpRequest: request.Request) -> str:
        with request.urlopen(httpRequest, timeout=self.timeout) as response:
            return response.read().decode("utf-8")
        
    def backoff_delay(self, attempt: int) -> float:
        exponential = min(
            self.retryPolicy.baseBackoff * (self.retryPolicy.backoffMultiplier ** attempt),
            self.retryPolicy.maxBackoff,
        )
        if self.retryPolicy.jitter == 0 or exponential == 0: 
            return exponential
        
        jitterCeiling = exponential * self.retryPolicy.jitter
        return min(
            exponential + uniform(0, jitterCeiling),
            self.retryPolicy.maxBackoff,
        )