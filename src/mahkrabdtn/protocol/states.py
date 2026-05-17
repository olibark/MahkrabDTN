from enum import StrEnum
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, field


from mahkrabdtn.protocol.node.registration import NodeRegistration
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.tools.parsing.time import parse_datetime


class DeliveryState(StrEnum):
    RECEIVED = "receivedByServer"
    QUEUED = "queued"
    DELIVERED_RECIPIENT = "delivered"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"
    
@dataclass(slots=True)
class RelayNodeState:
    nodeID: UUID
    lastSeen: datetime = field(default_factory=utcnow)
    publicKey: str | None = None
    isPolling: bool = False
    pendingMessageCount: int = 0
    
    def __post_init__(self) -> None:
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        self.lastSeen = parse_datetime(self.lastSeen, "lastSeen")
        
        if self.publicKey is not None and not isinstance(self.publicKey, str):
            raise TypeError("publicKey must be of type string")
        if not isinstance(self.isPolling, bool): raise TypeError("isPolling must be pf type bool")
        if not isinstance(self.pendingMessageCount, int): raise TypeError("pendingMessageCount must be of type int")
        if self.pendingMessageCount < 0: raise ValueError("pendingMessageCount must be positive")
        
    @classmethod
    def from_registration(cls, registration: NodeRegistration) -> "RelayNodeState":
        return cls(
            nodeID=registration.nodeID,
            lastSeen=registration.lastSeen,
            publicKey=registration.publicKey,
        )
        
    def apply_registration(self, registration: NodeRegistration) -> None:
        if self.nodeID != registration.nodeID: raise ValueError("registration nodeID does not match relay node state")
        
        self.lastSeen = parse_datetime(
            self.lastSeen, "lastSeen",
        )
        self.publicKey = registration.publicKey
        