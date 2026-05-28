from uuid import UUID
from datetime import datetime
from typing import Mapping, Any
from dataclasses import dataclass, field

from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.tools.parsing.time import parse_datetime


@dataclass(slots=True)
class PollResponse:
    nodeID: UUID
    messages: list[MessagePacket] = field(default_factory=list)
    serverTime: datetime = field(default_factory=utcnow)
    
    def __post_init__(self):
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        self.serverTime = parse_datetime(self.serverTime, "serverTime")
        self.messages = self.parse_messages(self.messages)
        
    @staticmethod
    def parse_messages(value: object) -> list[MessagePacket]: 
        if not isinstance(value, list):
            raise TypeError("messages must be of type list[MessagePacket]")
        
        messages: list[MessagePacket] = []
        
        for item in value:
            if isinstance(item, MessagePacket):
                messages.append(item)
                continue
            
            if isinstance(item, Mapping):
                messages.append(MessagePacket.from_dict(item))
                continue
            
            raise TypeError("messages must be of type list[NessagePacket] or list[Mapping]")
        
        return messages

    def to_dict(self) -> dict[str, object]:
        return {
            "nodeID": str(self.nodeID),
            "messages": [message.to_dict() for message in self.messages],
            "serverTime": self.serverTime.isoformat(),
        }
        
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PollResponse":
        return cls(
            nodeID=parse_uuid(data["nodeID"], "nodeID"),
            messages=cls.parse_messages(data.get("messages", [])),
            serverTime=parse_datetime(
                data.get("serverTime", utcnow()),
                "serverTime",
            ),
        )
