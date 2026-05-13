from uuid import UUID
from dataclasses import dataclass


@dataclass(slots=True)
class RelayNodeClient:
    baseURL: str
    nodeID: UUID
    privateKeyPem: str
    publicKeyPem: str
    processedMessageStore: pass