from dataclasses import dataclass

from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.protocol.states import DeliveryState
from mahkrabdtn.helpers.time import utcnow


@dataclass(slots=True)
class RelayMessageRecord:
    packet: MessagePacket
    state: DeliveryState = DeliveryState.RECEIVED
    
    def __post_init__(self) -> None:
        if not isinstance(self.packet, MessagePacket): raise TypeError("packet must be of type MessagePacket")
        if not isinstance(self.state, DeliveryState): self.state = DeliveryState(self.state)
        
    def mark_queued(self) -> None: self.state = DeliveryState.QUEUED    
    def mark_delivered(self) -> None: self.state = DeliveryState.DELIVERED_RECIPIENT
    def mark_acknowledged(self) -> None: self.state = DeliveryState.ACKNOWLEDGED
    def mark_expired(self) -> None: self.state = DeliveryState.EXPIRED
    
    def expire(self) -> bool:
        if self.state != DeliveryState.QUEUED: return False
        if not self.packet.is_expired(utcnow()): return False
        
        self.mark_expired()
        
        return True