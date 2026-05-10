from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID, uuid4

from mahkrabdtn.protocol.tools.time import utcnow
from mahkrabdtn.protocol.parsing.datetime import parse_datetime
from mahkrabdtn.protocol.parsing.uuid import parse_uuid
from mahkrabdtn.protocol.parsing.text import parse_text


@dataclass
class MessagePacket:
    senderID: UUID
    recipientID: UUID
    payload: str
    encryption: str
    expires: datetime | None = None
    version: str = "1.0"
    messageID: UUID = field(default_factory=uuid4)
    created: datetime = field(default_factory=utcnow)

    def __post_init__(self):
        self.senderID = parse_uuid(self.senderID, "senderID")
        self.recipientID = parse_uuid(self.recipientID, "recipientID")
        self.payload = parse_text(self.payload, "payload")