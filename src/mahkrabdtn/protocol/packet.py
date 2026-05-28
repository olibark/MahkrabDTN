from datetime import datetime
from typing import Any, Mapping
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from mahkrabdtn.crypto.metadata import EncryptionMetadata
from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.tools.parsing.text import parse_text
from mahkrabdtn.helpers.time import utcnow


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
        
        if isinstance(self.encryption, Mapping): 
            self.encryption = EncryptionMetadata.from_dict(self.encryption)
        elif not isinstance(self.encryption, EncryptionMetadata): raise TypeError("encryption must be of type EncryptionMetadata or Mapping")
        
        if self.expires is not None: 
            self.expires = parse_datetime(self.expires, "expires") 
        
        self.version = parse_text(self.version, "version")
        self.messageID = parse_uuid(self.messageID, "messageID")
        self.created = parse_datetime(self.created, "created")
        
        if self.expires is not None and self.expires <= self.created:
            raise ValueError("expires at must be later than created at")
        
    def is_expired(self, referenceTime: datetime | None = None) -> bool:
        if self.expires is None:
            return False
        comparisonTime = utcnow() if referenceTime is None else parse_datetime(
            referenceTime,
            "referenceTime",
        )   
        
        return self.expires <= comparisonTime
    
    def to_dict(self) -> dict[str, object]:
        payload = {
            "messageID": str(self.messageID),
            "senderID": str(self.senderID),
            "recipientID": str(self.recipientID),
            "created": str(self.created),
            "payload": self.payload,
            "encryption": self.encryption.to_dict(),
            "version": self.version,
        }
        if self.expires is not None:
            payload["expires"] = self.expires.isoformat()
            
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MessagePacket":
        return cls(
            messageID=parse_uuid(data["messageID"], "messageID"),
            senderID=parse_uuid(data["senderID"], "senderID"),
            recipientID=parse_uuid(data["recipientID"], "recipientID"),
            created=parse_datetime(data["created"], "created"),
            payload=parse_text(data["payload"], "payload"),
            encryption=EncryptionMetadata.from_dict(data.get("encryption", {})),
            expires=(
                parse_datetime(data["expires"], "expire")
                if data.get("expires") is not None 
                else None
            ),
            version=parse_text(data.get("version", "1.0"), "version"),
        )
