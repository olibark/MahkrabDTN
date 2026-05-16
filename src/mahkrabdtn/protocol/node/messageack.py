from datetime import datetime
from typing import Any, Mapping
from uuid import UUID
from dataclasses import field, dataclass

from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.helpers.time import utcnow


@dataclass(slots=True)
class MessageAcknowledgment:
    messageID: UUID
    nodeID: UUID
    acknowledgedAt: datetime = field(default_factory=utcnow)
    
    def __post_init__(self) -> None:
        self.messageID = parse_uuid(self.messageID, "messageID")
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        self.acknowledgedAt = parse_datetime(
            self.acknowledgedAt,
            "acknowledgedAt",
        )
        
    def to_dict(self) -> dict[str, str]:
        return {
            "messageID": str(self.messageID),
            "nodeID": str(self.nodeID),
            "acknowledgedAt": self.acknowledgedAt.isoformat(),
        }
        
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MessageAcknowledgment":
        return cls(
            messageID=parse_uuid(data["messageID"], "messageID"),
            nodeID=parse_uuid(data["nodeID"], "nodeID"),
            acknowledgedAt=parse_datetime(
                data.get("acknowledgedAt", utcnow()),
                "acknowledgedAt",
            ),
        )