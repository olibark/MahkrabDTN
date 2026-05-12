from enum import StrEnum


class DeliveryState(StrEnum):
    RECEIVED = "receivedByServer"
    QUEUED = "queued"
    DELIVERED_RECIPIENT = "delivered"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"