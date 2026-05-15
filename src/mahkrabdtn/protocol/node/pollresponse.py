from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, field

from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid

@dataclass(slots=True)
class PollResponse:
    nodeID: UUID
    messages: list[MessagePacket] = field(default_factory=list)
    serverTime: datetime = field(default_factory=utcnow)
    
    def __post_init__(self):
        self.nodeID = parse_uuid(self.nodeID, "nodeID")
        if not isinstance(self.messages, list):
            raise TypeError("messages must be of type list[MessagePacket]")