from datetime import datetime
from uuid import UUID
from threading import RLock
import logging
from dataclasses import dataclass, field

from mahkrabdtn.server.messagerecord import RelayMessageRecord
from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.protocol.states import DeliveryState
from mahkrabdtn.server.messageack import MessageAcknowledgment
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class InMemoryMessageStore:
    messageRecords: dict[UUID, RelayMessageRecord] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock, repr=False)
    
    def accept_message(self, packet: MessagePacket) -> RelayMessageRecord:
        with self.lock:
            existing = self.messageRecords.get(packet.messageID)
            if existing is not None: 
                if existing != packet:
                    raise ValueError(
                        f"messageID already exist with a different packet: {packet.messageID}"
                    )
                existing.expire()
                
                logger.info(
                    "relay.store.duplicate_message",
                    extra={
                        "messageID": str(packet.messageID),
                        "state": existing.state.value,
                        "storageBackend": "memory",
                    },
                )
                return existing

            record = RelayMessageRecord(packet=packet)
            
            if packet.is_expired(utcnow()): record.mark_expired()
            else: record.mark_queued()
            
            self.messageRecords[packet.messageID] = record
            
            logger.info(
                "relay.store.message_state_changed",
                extra={
                    "messageID": str(packet.messageID),
                    "recipientID": str(packet.recipientID),
                    "state": record.state.value,
                    "storageBackend": "memory",
                },
            )
            
            return record
    
    def get_message_record(self, messageID: UUID) -> RelayMessageRecord | None:
        messageID = parse_uuid(messageID, "messageID")
        
        with self.lock:
            record = self.messageRecords.get(messageID)
            
            if record is not None: record.expire()
            
            return record
        
    def list_recipient_messages(self, recipientID: UUID, state: DeliveryState | None = None) -> list[RelayMessageRecord]:
        recipientID = parse_uuid(recipientID, "recipientID")
        
        with self.lock:
            self.cleanup_expired_messages()
            matchingRecords = [
                record for record in self.messageRecords.values()
                if record.packet.recipientID == recipientID
            ]
            
            if state is None: return list(matchingRecords)
            
            return [record for record in matchingRecords if record.state == state]
        
    def count_queued_messages(self, recipientID: UUID) -> int:
        return len(
            self.list_recipient_messages(
                recipientID,
                state=DeliveryState.QUEUED,
            )
        )
        
    def deliver_queued_messages(self, recipientID: UUID) -> list[RelayMessageRecord]:
        recipientID = parse_uuid(recipientID, "recipientID")
        
        with self.lock:
            self.cleanup_expired_messages()
            queuedRecords = [
                record for record in self.messageRecords.values()
                if record.packet.recipientID == recipientID
                and record.state == DeliveryState.QUEUED
            ]
            for record in queuedRecords: 
                record.mark_delivered()
                logger.info(
                    "relay.store.message_state_changed",
                    extra={
                        "messageID": str(record.packet.messageID),
                        "recipientID": str(record.packet.recipientID),
                        "state": record.state.value,
                        "storageBackend": "memory",
                    },
                )
                
            return list(queuedRecords)

    def acknowledge_message(self, acknowledgement: MessageAcknowledgment) -> RelayMessageRecord:
        with self.lock:
            record = self.get_message_record(acknowledgement.messageID)
            
            if record is None: raise KeyError(f"unknowk messageID: {acknowledgement.messageID}")
            if record.packet.recipientID != acknowledgement.nodeID: raise ValueError("acknowledgment nodeID does not match recipientID")
            
            if record.state == DeliveryState.ACKNOWLEDGED:
                logger.info(
                    "relay.state.duplicate_acknowledgment",
                    extra={
                        "messageID": str(record.packet.messageID),
                        "recipientID": str(record.packet.recipientID),
                        "storageBackend": "memory",
                    },
                )
                
                return record
            
            if record.state == DeliveryState.EXPIRED: raise ValueError("message expired")
            if record.state != DeliveryState.DELIVERED_RECIPIENT: raise ValueError("message is not ready to be acknowledged, silly")
            
            record.mark_acknowledged()
        
            logger.info(
                "relay.store.message_state_changed",
                extra={
                    "messageID": str(record.packet.messageID),
                    "recipientID": str(record.packet.recipientID),
                    "state": record.state.value,
                    "storageBackend": "memory",
                },
            )
            return record
        
    def cleanup_expired_messages(self, referenceTime: datetime | None = None) -> list[RelayMessageRecord]:
        effectiveReferenceTime = utcnow() if referenceTime is None else referenceTime
        
        with self.lock:
            expiredRecords: list[RelayMessageRecord] = []
            
            for record in self.messageRecords.values():
                if record.state == DeliveryState.QUEUED and record.packet.is_expired(
                    effectiveReferenceTime
                ):
                    record.mark_expired()
                    expiredRecords.append(record)
                    
                    logger.info(
                        "relay.store.message_state_changed",
                        extra={
                            "messageID": str(record.packet.messageID),
                            "recipientID": str(record.packet.recipientID),
                            "state": record.state.value,
                            "storageBackend": "memory",
                        },
                    )
            return expiredRecords