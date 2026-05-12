from dataclasses import dataclass
from datetime import datetime

from mahkrabdtn.protocol.parsing.text import parse_text
from mahkrabdtn.protocol.parsing.uuid import parse_uuid


@dataclass(Slots=True)
class NodeRegistration:
    nodeID: str
    lastSeen: datetime
    publicKey: str
    
    def __post_init__(self):
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        self.lastSeen = parse_text(self.lastSeen, "lastSeen")
        if self.publicKey is not None: self.publicKey = parse_text(self.publicKey, "publicKey")
            
    def to_dict(self) -> dict[str, str]:
        payload = {
            "nodeID": self.nodeID,
            "lastSeen": self.lastSeen.isoformat(),
        }
        if self.publicKey is not None: 
            payload["publicKey"] = self.publicKey
            
        return payload