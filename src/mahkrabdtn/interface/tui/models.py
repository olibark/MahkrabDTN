from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.tools.parsing.uuid import parse_uuid


MessageDirection = Literal["inbound", "outbound", "system"]


@dataclass(slots=True)
class ConversationMessage:
    direction: MessageDirection
    payload: str
    peerID: UUID | None = None
    messageID: UUID | None = None
    created: datetime = field(default_factory=utcnow)
    state: str | None = None

    def __post_init__(self) -> None:
        self.created = parse_datetime(self.created, "created")

        if self.peerID is not None:
            self.peerID = parse_uuid(self.peerID, "peerID")

        if self.messageID is not None:
            self.messageID = parse_uuid(self.messageID, "messageID")
