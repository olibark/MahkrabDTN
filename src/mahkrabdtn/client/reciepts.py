from uuid import UUID
from dataclasses import dataclass
from typing import Mapping


from mahkrabdtn.protocol.states import DeliveryState
from mahkrabdtn.tools.parsing.uuid import parse_uuid


@dataclass(slots=True)
class MessageSubmissionReceipt:
    messageID: UUID
    state: DeliveryState
    
    def to_dict(self) -> dict[str, str]:      
        return {
            "messageID": str(self.messageID),
            "state": self.state.value,
        }
    
    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> "MessageSubmissionReceipt":
        return cls(
            messageID=parse_uuid(data["messageID"], "messageID"),
            state=DeliveryState(data["state"]),
        )
        
@dataclass(slots=True)
class MessageAcknowledgmentReceipt:
    messageID: UUID
    state: DeliveryState
    
    def to_dict(self) -> dict[str, str]:
        return {
            "messageID": str(self.messageID),
            "state": self.state.value,
        }
        
    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> "MessageAcknowledgmentReceipt":
        return cls(
            messageID=parse_uuid(data["messageID"], "messageID"),
            state=DeliveryState(data["state"])
        )
