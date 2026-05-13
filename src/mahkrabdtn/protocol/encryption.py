from dataclasses import dataclass
from typing import Any, Mapping

from mahkrabdtn.tools.parsing.text import parse_text


@dataclass
class EncryptionMetadata:
    algorithm: str = "none"
    encoding: str = "utf-8"
    recipientKeyID: str | None = None
    
    def __post_init__(self):
        self.algorithm = parse_text(self.algorithm, "algorithm")
        self.encoding = parse_text(self.encoding, "encoding")
        if self.recipientKeyID is not None:
            self.recipientKeyID = parse_text(
                self.recipientKeyID, "recipientKeyID"
            )
    
    def to_dict(self) -> dict[str, str]:
        payload = {
            "algorithm": self.algorithm,
            "encoding": self.encoding,
        }
    
        if self.recipientKeyID is not None:
            payload["recipientKeyID"] = self.recipientKeyID
        
        return payload