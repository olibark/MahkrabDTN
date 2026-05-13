from typing import Mapping, Any
from datetime import datetime
from dataclasses import dataclass, field

from mahkrabdtn.tools.parsing.text import parse_text
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.helpers.time import utcnow

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
    
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NodeRegistration":
        return cls(
            nodeId=parse_uuid(data["nodeID"], "nodeID"),
            lastSeen=parse_datetime(
                data.get("lastSeen", utcnow()),
                "lastSeen",
            )
        )