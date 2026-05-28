from datetime import datetime
from threading import RLock
from uuid import UUID
import logging
from dataclasses import dataclass, field

from mahkrabdtn.server.messagerecord import RelayMessageRecord
from mahkrabdtn.protocol.packet import MessagePacket
from mahkrabdtn.protocol.states import DeliveryState
from mahkrabdtn.server.messageack import MessageAcknowledgment
from mahkrabdtn.helpers.time import utcnow
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.server.sql.sqlite import connect_database


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SQLiteMessageStore:
    databasePath: str
    lock: RLock = field(default_factory=RLock, repr=False)
    
    def __post_init__(self) -> None:
        with self.lock:
            self.initialize_schema()
            
    def initialize_schema(self) -> None:
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relayMessages (
                    messageID TEXT PRIMARY KEY,
                    senderID TEXT NOT NULL,
                    recipientID TEXT NOT NULL,
                    created TEXT NOT NULL,
                    expires TEXT,
                    payload TEXT NOT NULL,
                    encryptionAlgorithm TEXT NOT NULL,
                    encryptionEncoding TEXT NOT NULL,
                    recipientKeyID TEXT,
                    version TEXT NOT NULL,
                    state TEXT NOT NULL
                )
                """
            )
            oldRelayMessagesExists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'relay_messages'
                """
            ).fetchone()
            if oldRelayMessagesExists is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO relayMessages (
                        messageID,
                        senderID,
                        recipientID,
                        created,
                        expires,
                        payload,
                        encryptionAlgorithm,
                        encryptionEncoding,
                        recipientKeyID,
                        version,
                        state
                    )
                    SELECT
                        message_id,
                        sender_id,
                        recipient_id,
                        created_at,
                        expires_at,
                        payload,
                        encryption_algorithm,
                        encryption_encoding,
                        recipient_key_fingerprint,
                        version,
                        CASE state
                            WHEN 'received_by_server' THEN 'receivedByServer'
                            WHEN 'delivered_to_recipient' THEN 'delivered'
                            ELSE state
                        END
                    FROM relay_messages
                    """
                )
            connection.commit()
            
    def accept_message(self, packet: MessagePacket) -> RelayMessageRecord:
        with self.lock:
            existing = self.get_message_record(packet.messageID)
            if existing is not None:
                if existing.packet != packet:
                    raise ValueError(
                        f"messageID already exists with a different packet: {packet.messageID}"
                    )
                existing.expire()
                self.upsert_record(existing)
                
                logger.info(
                    "relay.store.duplicate_message",
                    extra={
                        "messageID": str(packet.messageID),
                        "state": existing.state.value,
                        "storageBackend": "sqlite",
                    },
                )
                return existing
            
            record = RelayMessageRecord(packet=packet)
            
            if packet.is_expired(utcnow()): record.mark_expired()
            else: record.mark_queued()
            
            self.upsert_record(record)
            
            logger.info(
                "relay.store.message_state_changed",
                extra={
                    "messageID": str(packet.messageID),
                    "recipientID": str(packet.recipientID),
                    "state": record.state.value,
                    "storageBackend": "sqlite",
                },
            )
            
            return record
        
    def get_message_record(self, messageID: UUID) -> RelayMessageRecord | None:
        messageID = parse_uuid(messageID, "messageID")
        
        with self.lock:
            self.cleanup_expired_messages()
            with connect_database(self.databasePath) as connection:
                row = connection.execute(
                    """
                    SELECT
                        messageID,
                        senderID,
                        recipientID,
                        created,
                        expires,
                        payload,
                        encryptionAlgorithm,
                        encryptionEncoding,
                        recipientKeyID,
                        version,
                        state
                    FROM relayMessages
                    WHERE messageID = ?
                    """,
                    (str(messageID),),
                ).fetchone()
                
            if row is None: return None
            
            return self.record_from_row(row)
        
    def list_recipient_messages(
        self,
        recipientID: UUID,
        state: DeliveryState | None = None,
    ) -> list[RelayMessageRecord]:
        
        recipientID = parse_uuid(recipientID, "recipientID")
        
        with self.lock:
            self.cleanup_expired_messages()
            with connect_database(self.databasePath) as connection:
                if state is None:
                    rows = connection.execute(
                        """
                        SELECT
                            messageID,
                            senderID,
                            recipientID,
                            created,
                            expires,
                            payload,
                            encryptionAlgorithm,
                            encryptionEncoding,
                            recipientKeyID,
                            version,
                            state
                        FROM relayMessages
                        WHERE recipientID = ?
                        ORDER BY created
                        """,
                        (str(recipientID),),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT
                            messageID,
                            senderID,
                            recipientID,
                            created,
                            expires,
                            payload,
                            encryptionAlgorithm,
                            encryptionEncoding,
                            recipientKeyID,
                            version,
                            state
                        FROM relayMessages
                        WHERE recipientID = ? AND state = ?
                        ORDER BY created
                        """,
                        (str(recipientID), state.value),
                    ).fetchall()
                    
            return [self.record_from_row(row) for row in rows]
        
    def count_queued_messages(self, recipientID: UUID) -> int:
        recipientID = parse_uuid(recipientID, "recipientID")
        
        with self.lock:
            self.cleanup_expired_messages()
            with connect_database(self.databasePath) as connection:
                row = connection.execute(
                    """
                    SELECT COUNT(*) AS queuedCount
                    FROM relayMessages
                    WHERE recipientID = ? AND state = ?
                    """,
                    (str(recipientID), DeliveryState.QUEUED.value),
                ).fetchone()
            
            return int(row["queuedCount"])
        
    def deliver_queued_messages(self, recipientID: UUID) -> list[RelayMessageRecord]:
        recipientID = parse_uuid(recipientID, "recipientID")
        
        with self.lock:
            self.cleanup_expired_messages()
            queuedRecords = self.list_recipient_messages(
                recipientID,
                state=DeliveryState.QUEUED,
            )
            
            for record in queuedRecords:
                record.mark_delivered()
                self.upsert_record(record)
                logger.info(
                    "relay.store.message_state_changed",
                    extra={
                        "messageID": str(record.packet.messageID),
                        "recipientID": str(record.packet.recipientID),
                        "state": record.state.value,
                        "storageBackend": "sqlite",
                    },
                )
                
            return queuedRecords
        
    def acknowledge_message(self, acknowledgement: MessageAcknowledgment) -> RelayMessageRecord:
        with self.lock:
            record = self.get_message_record(acknowledgement.messageID)
            
            if record is None: raise KeyError(f"unknown messageID: {acknowledgement.messageID}")
            if record.packet.recipientID != acknowledgement.nodeID: raise ValueError("acknowledgment nodeID does not match recipientID")
            
            if record.state == DeliveryState.ACKNOWLEDGED:
                logger.info(
                    "relay.store.duplicate_acknowledgment",
                    extra={
                        "messageID": str(record.packet.messageID),
                        "recipientID": str(record.packet.recipientID),
                        "storageBackend": "sqlite",
                    },
                )
                
                return record
            
            if record.state == DeliveryState.EXPIRED: raise ValueError("message expired")
            if record.state != DeliveryState.DELIVERED_RECIPIENT: raise ValueError("message is not ready to be acknowledged, silly")
            
            record.mark_acknowledged()
            self.upsert_record(record)
        
            logger.info(
                "relay.store.message_state_changed",
                extra={
                    "messageID": str(record.packet.messageID),
                    "recipientID": str(record.packet.recipientID),
                    "state": record.state.value,
                    "storageBackend": "sqlite",
                },
            )
            return record
        
    def cleanup_expired_messages(self, referenceTime: datetime | None = None) -> int:
        effectiveReferenceTime = utcnow() if referenceTime is None else referenceTime
        
        with self.lock:
            with connect_database(self.databasePath) as connection:
                cursor = connection.execute(
                    """
                    UPDATE relayMessages
                    SET state = ?
                    WHERE state = ? AND expires IS NOT NULL AND expires <= ?
                    """,
                    (
                        DeliveryState.EXPIRED.value,
                        DeliveryState.QUEUED.value,
                        effectiveReferenceTime.isoformat(),
                    ),
                )
                connection.commit()
                
                expiredCount = int(cursor.rowcount)
                if expiredCount:
                    logger.info(
                        "relay.store.expired_cleanup",
                        extra={
                            "expiredCount": expiredCount,
                            "storageBackend": "sqlite",
                        },
                    )
                    
                return expiredCount
        
    def upsert_record(self, record: RelayMessageRecord) -> None:
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                INSERT INTO relayMessages (
                    messageID,
                    senderID,
                    recipientID,
                    created,
                    expires,
                    payload,
                    encryptionAlgorithm,
                    encryptionEncoding,
                    recipientKeyID,
                    version,
                    state
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(messageID) DO UPDATE SET
                    senderID = excluded.senderID,
                    recipientID = excluded.recipientID,
                    created = excluded.created,
                    expires = excluded.expires,
                    payload = excluded.payload,
                    encryptionAlgorithm = excluded.encryptionAlgorithm,
                    encryptionEncoding = excluded.encryptionEncoding,
                    recipientKeyID = excluded.recipientKeyID,
                    version = excluded.version,
                    state = excluded.state
                """,
                (
                    str(record.packet.messageID),
                    str(record.packet.senderID),
                    str(record.packet.recipientID),
                    record.packet.created.isoformat(),
                    (
                        record.packet.expires.isoformat()
                        if record.packet.expires is not None
                        else None
                    ),
                    record.packet.payload,
                    record.packet.encryption.algorithm,
                    record.packet.encryption.encoding,
                    record.packet.encryption.recipientKeyID,
                    record.packet.version,
                    record.state.value,
                ),
            )
            connection.commit()
            
    def record_from_row(self, row) -> RelayMessageRecord:
        return RelayMessageRecord(
            packet=MessagePacket(
                messageID=row["messageID"],
                senderID=row["senderID"],
                recipientID=row["recipientID"],
                created=row["created"],
                expires=row["expires"],
                payload=row["payload"],
                encryption={
                    "algorithm": row["encryptionAlgorithm"],
                    "encoding": row["encryptionEncoding"],
                    "recipientKeyID": row["recipientKeyID"],
                },
                version=row["version"],
            ),
            state=DeliveryState(row["state"]),
        )
