from typing import Any, Iterable
from json import JSONDecodeError
from io import BytesIO
from uuid import UUID
import json
import logging
from urllib.parse import parse_qs
from time import sleep, monotonic

from mahkrabdtn.server.registry import InMemoryNodeRegistry
from mahkrabdtn.server.sql.sqliteregistry import SQLiteNodeRegistry
from mahkrabdtn.server.sql.sqlitemessagestore import SQLiteMessageStore
from mahkrabdtn.server.messagestore import InMemoryMessageStore
from mahkrabdtn.protocol.node.registration import NodeRegistration
from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.server.messageack import MessageAcknowledgment
from mahkrabdtn.protocol.node.pollresponse import PollResponse
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid

logger = logging.getLogger(__name__)


class RelayApplication:
    def __init__(
        self, 
        nodeRegistry: InMemoryNodeRegistry | None = None,
        messageStore: InMemoryMessageStore | None = None,
        pollInterval_ms: int = 50,
        databasePath: str | None = None,
    ) -> None:
        
        if pollInterval_ms <= 0: raise ValueError("pollInterval_ms must be positive")
        if databasePath is not None and (nodeRegistry is not None or messageStore is not None):
            raise ValueError("databasePath cannot be combined with custom registry or store")
        
        if databasePath is not None: 
            self.nodeRegistry = SQLiteNodeRegistry(databasePath=databasePath)
            self.messageStore = SQLiteMessageStore(databasePath=databasePath)
            self.storageBackend = "sqlite"
            
        else:
            self.nodeRegistry = nodeRegistry or InMemoryNodeRegistry()
            self.messageStore = messageStore or InMemoryMessageStore()
            self.storageBackend = "memory"
        
        self.pollInterval_ms: int = pollInterval_ms
        
    def __call__(self, environ: dict[str, Any], startResponse: Any) -> Iterable[bytes]:
        requestMethod = str(environ.get("REQUEST_METHOD", ""))
        pathInfo = str(environ.get("PATH_INFO", ""))
        
        match pathInfo:
            case "/healthsz": return self.handle_health_check(requestMethod, startResponse)
            case "/nodes/register": return self.handle_node_registration(requestMethod, environ, startResponse)
            case path if path.startswith("/nodes/"): return self.handle_node_lookup(requestMethod, pathInfo, startResponse)
            case "/messages": return self.handle_message_submission(requestMethod, environ, startResponse)
            case "/messages/poll": return self.handle_message_poll(requestMethod, environ, startResponse)
            case path if path.startswith("/messages/") and path.endswith("/ack"):
                return self.handle_message_acknowledgment(requestMethod, pathInfo, environ, startResponse)
            
        return self.respond_json(
            startResponse,
            "404 Not Found",
            {"error": "route not found haha"},
        )
        
    def handle_health_check(self, requestMethod: str, startResponse: Any) -> Iterable[bytes]:
        if requestMethod != "GET":
            return self.respond_json(
                startResponse,
                "405 Method Not Allowed",
                {"error": "method not allowed :("},
            )
        
        return self.respond_json(
            startResponse,
            "200 OK",
            {
                "status": "ok",
                "serverTime": utcnow().isoformat(),
                "storageBackend": self.storageBackend, 
                "pollInterval_ms": self.pollInterval_ms,
            },
        )
        
    def handle_node_registration(
        self, 
        requestMethod: str, 
        environ: dict[str, Any], 
        startResponse: Any
    ) -> Iterable[bytes]:
        
        if requestMethod != "POST":
            return self.respond_json(
                startResponse, 
                "405 Method Not Allowed",
                {"error": "method not allowed :)"},
            )
        
        try: 
            requestData = self.read_json_body(environ)
            registration = NodeRegistration.from_dict(requestData)
            state = self.nodeRegistry.register_node(registration)
            pendingMessageCount = self.messageStore.count_queued_messages(
                state.nodeID
            )
            state = self.nodeRegistry.set_pending_message_count(
                state.nodeID,
                pendingMessageCount,
            )
            
            logger.info(
                "relay.node.registered",
                extra={
                    "nodeID": str(state.nodeID),
                    "pendingMessageCount": pendingMessageCount,
                    "hasPublicKey": state.publicKey is not None,
                },
            )
            
        except (JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.warning(
                "relay.node.register.failed",
                extra={
                    "error": str(error),
                }
            )
            return self.respond_json(
                startResponse,
                "400 Bad Request naughty",
                {"error": str(error)},
            )
            
        responseRegistration = NodeRegistration(
            nodeID=state.nodeID,
            lastSeen=state.lastSeen,
            publicKey=state.publicKey,
        )
        
        return self.respond_json(
            startResponse,
            "200 OK",
            responseRegistration.to_dict(),
        )
        
    def handle_node_lookup(self, requestMethod: str, pathInfo: str, startResponse: Any) -> Iterable[bytes]:
        if requestMethod != "GET":
            return self.respond_json(
                startResponse,
                "405 Method Not Allowed",
                {"error": "method not allowed"},
            )
            
        try:
            nodeID = self.read_nodeID_from_node_path(pathInfo)
            state = self.nodeRegistry.require_node_state(nodeID)
            logger.info(
                "relay.node.lookup",
                extra={
                    "nodeID": str(state.nodeID),
                    "hasPublicKey": state.publicKey is not None,
                },
            )
            
        except KeyError:
            logger.warning(
                "relay.node.lookup.not_found",
                extra={"path": pathInfo},
            )
            return self.respond_json(
                startResponse,
                "404 Not Found",
                {"error": "node not found"},
            )
            
        registration = NodeRegistration(
            nodeID=state.nodeID,
            lastSeen=state.lastSeen,
            publicKey=state.publicKey,
        )
        return self.respond_json(
            startResponse,
            "200 OK",
            registration.to_dict(),
        )
        
    def handle_message_submission(
        self,
        requestMethod: str,
        environ: dict[str, Any],
        startResponse: Any,
    ) -> Iterable[bytes]:
        
        if requestMethod != "POST": 
            return self.respond_json(
                startResponse,
                "405 Method Not Allowed",
                {"error": "method not allowed"},
            )
            
        try:
            requestData = self.read_json_body(environ)
            packet = MessagePacket.from_dict(requestData)
            record = self.messageStore.accept_message(packet)
            recipientState = self.nodeRegistry.get_node_state(packet.recipientID)
            
            if recipientState is not None:
                queuedCount = self.messageStore.count_queued_messages(
                    packet.recipientID
                )
                self.nodeRegistry.set_pending_message_count(
                    packet.recipientID,
                    queuedCount,
                )
            
            logger.info(
                "relay.message.accepted",
                extra={
                    "messageID": str(record.packet.messageID),
                    "senderID": str(record.packet.senderID),
                    "recipientID": str(record.packet.recipientID),
                    "state": record.state.value,
                    "expiresAt": (
                        record.packet.expires.isoformat()
                        if record.packet.expires is not None
                        else None
                    ),
                },
            )
            
        except (JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.warning(
                "relay.message.accept.failed",
                extra={"error": str(error)},
            )
            return self.respond_json(
                startResponse,
                "400 Bad Request",
                {"error": str(error)},
            )
        
        return self.respond_json(
            startResponse,
            "202 Accepted",
            {
                "messageID": str(record.packet.messageID),
                "state": record.state.value,
            },
        )
    
    def handle_message_poll(
        self,
        requestMethod: str,
        environ: dict[str, Any],
        startResponse: Any,
    ) -> Iterable[bytes]:
        
        if requestMethod != "GET":
            return self.respond_json(
                startResponse,
                "405 Method Not Allowed",
                {"error": "method not allowed"},
            )
        
        try: 
            nodeID = self.read_nodeID_from_query(environ)
            timeout_ms = self.read_timeout_ms_from_query(environ)
            logger.info(
                "relay.poll.stared",
                extra={"nodeID": str(nodeID), "timeout_ms": timeout_ms},
            )
            nodeState= self.nodeRegistry.require_node_state(nodeID)
            self.nodeRegistry.set_polling_state(nodeState.nodeID, True)
            
            try: response = self.wait_for_poll_response(nodeState.nodeID, timeout_ms)
            finally: self.nodeRegistry.set_polling_state(nodeState.nodeID, False)
            
            logger.info(
                "relay.poll.completed",
                extra={
                    "nodeID": str(response.nodeID),
                    "timeout_ms": timeout_ms,
                    "messageCount": len(response.messages),
                },
            )
            
        except (KeyError, TypeError, ValueError) as error:
            logger.warning(
                "relay.poll.failed",
                extra={"error": str(error)},
            )
            return self.respond_json(
                startResponse,
                "400 Bad Request",
                {"error": str(error)},
            )
            
        return self.respond_json(
            startResponse,
            "200 OK",
            response.to_dict(),
        )
    
    def handle_message_acknowledgment(
        self,
        requestMethod: str,
        pathInfo: str,
        environ: dict[str, Any],
        startResponse: Any,
    ) -> Iterable[bytes]:
        
        if requestMethod != "POST": 
            return self.respond_json(
                startResponse,
                "405 Method Not Allowed",
                {"error": "method not allowed"},
            )
            
        try:
            pathMessageID = self.read_messageID_from_path(pathInfo)
            requestData = self.read_json_body(environ)
            acknowledgment = MessageAcknowledgment.from_dict(requestData)
            
            if acknowledgment.messageID != pathMessageID: raise ValueError("messageID in path does not match request body")
            
            record = self.messageStore.acknowledge_message(acknowledgment)
            
            logger.info(
                "relay.message.acknowledged",
                extra={
                    "messageID": str(record.packet.messageID),
                    "nodeID": str(acknowledgment.nodeID),
                    "state": record.state.value,
                },
            )
            
        except (JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.warning(
                "relay.message.ack.failed",
                extra={"path": pathInfo, "error": str(error)},
            )
            return self.respond_json(
                startResponse,
                "400 Bad Request",
                {"error": str(error)},
            )

        return self.respond_json(
            startResponse,
            "200 OK",
            {
                "messageID": str(record.packet.messageID),
                "state": record.state.value,
            },
        )
        
    def read_json_body(self, environ: dict[str, Any]) -> dict[str, Any]:
        contentLength = str(environ.get("CONTENT_LENGTH", "0")).strip() or "0"
        contentLength = int(contentLength)
        requestBodyStream = environ.get("wsgi.input", BytesIO())
        rawBody = requestBodyStream.read(contentLength)
        decodedBody = rawBody.decode("utf-8") if rawBody else "{}"
        parsedBody = json.loads(decodedBody)
        
        if not isinstance(parsedBody, dict): raise TypeError("request body must be of type dict")
        
        return parsedBody
    
    def read_nodeID_from_query(self, environ: dict[str, Any]) -> str:
        rawQuery = str(environ.get("QUERY_STRING", ""))
        parsedQuery = parse_qs(rawQuery, keep_blank_values=True)
        nodeIDValues = parsedQuery.get("nodeID")
        
        if not nodeIDValues or not nodeIDValues[0]: raise ValueError("nodeID query parameter is required")
        
        return nodeIDValues[0]
    
    def read_timeout_ms_from_query(self, environ: dict[str, Any]) -> int:
        rawQuery = str(environ.get("QUERY_STRING", ""))
        parsedQuery = parse_qs(rawQuery, keep_blank_values=True)
        timeoutValues = parsedQuery.get("timeout_ms")
        
        if not timeoutValues or timeoutValues[0] == "": return 0
        
        timeout_ms = int(timeoutValues[0])
        
        if timeout_ms < 0: raise ValueError("timeout_ms must be positive")
        
        return timeout_ms
    
    def read_messageID_from_path(self, pathInfo: str) -> UUID:
        pathParts = [part for part in pathInfo.split("/") if part]
        
        if len(pathParts) != 3 or pathParts[0] != "messages" or pathParts[2] != "ack":
            raise ValueError("incalid acknowledgement path")
        
        return parse_uuid(pathParts[1], "messageID")
    
    def read_nodeID_from_node_path(self, pathInfo: str) -> UUID:
        pathParts = [part for part in pathInfo.split("/") if part]

        if len(pathParts) != 2 or pathParts[0] != "nodes": raise ValueError("invalid node lookup path")
        
        return parse_uuid(pathParts[1], "nodeID")
    
    def wait_for_poll_response(self, nodeID: str, timeout_ms: int) -> PollResponse:
        deadline = monotonic() + (timeout_ms / 1000)
        
        while True:
            response = self.build_poll_response(nodeID)
            if response.messages: return response
            if monotonic() >= deadline: return response
            
            sleep(self.pollInterval_ms / 1000)
            
    def build_poll_response(self, nodeID: str) -> PollResponse:
        nodeState = self.nodeRegistry.require_node_state(nodeID)
        registration = NodeRegistration(
            nodeID=nodeState.nodeID,
            lastSeen=utcnow(),
            publicKey=nodeState.publicKey,
        )
        nodeState = self.nodeRegistry.register_node(registration)
        deliveredRecords = self.messageStore.deliver_queued_messages(nodeState.nodeID)
        queuedCount = self.messageStore.count_queued_messages(
            nodeState.nodeID,    
        )
        self.nodeRegistry.set_pending_message_count(nodeState.nodeID, queuedCount)
        
        return PollResponse(
            nodeID=nodeState.nodeID,
            messages=[record.packet for record in deliveredRecords],
        )
        
    def respond_json(self, startResponse: Any, status: str, payload: dict[str, Any]) -> Iterable[bytes]:
        responseBody = json.dumps(payload).encode("utf-8")
        responseHeaders = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(responseBody))),
        ]
        startResponse(status, responseHeaders)
        
        return [responseBody]
