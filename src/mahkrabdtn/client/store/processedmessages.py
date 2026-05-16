from pathlib import Path
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field

from mahkrabdtn.client.networking.policys import ProcessedMessageRetentionPolicy
from mahkrabdtn.tools.database.connect import connect_database
from mahkrabdtn.helpers.resolve import resolve_processed_messages_path
from mahkrabdtn.tools.parsing.uuid import parse_uuid
from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.helpers.time import utcnow


@dataclass(slots=True)
class ProcessedMessagesStore:
    databasePath: Path
    retentionPolicy: ProcessedMessageRetentionPolicy = field(
        default_factory=ProcessedMessageRetentionPolicy
    )
    
    @classmethod
    def from_identity_path(cls, identityPath: str | Path) -> "ProcessedMessagesStore":
        store = cls(
            databasePath=resolve_processed_messages_path(identityPath)
        )
        return store
   
    def __post_init__(self):
        self.databasePath = Path(self.databasePath)
        self.databasePath.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(self.retentionPolicy, ProcessedMessageRetentionPolicy): 
            raise TypeError("retentionPolicy must be of type ProcessedMessageRetentionPolicy")
        self.initialize_schema()
        self.prune()
        
    def initialize_schema(self) -> None:
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processedMessages (
                    messageID TEXT PRIMARY KEY,
                    processedAt TEXT NOT NULL
                )
                """
            )
            connection.commit()
            
    def processed_message(self, messageID: UUID) -> bool:
        messageID = parse_uuid(messageID, "messageID")
        with connect_database(self.databasePath) as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM processedMessages
                WHERE messageID = ?
                """,
                (str(messageID),),
            ).fetchone()
            
        return row is not None
    
    def mark_processed(self, messageID: UUID, saveTime: datetime | None = None) -> None:
        messageID = parse_uuid(messageID, "messageID")
        processedAt = utcnow() if saveTime is None else parse_datetime(saveTime, "saveTime")
        
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                INSERT INTO processedMessages (
                    messageID, processedAt
                )
                VALUES (?, ?)
                ON CONFLICT(messageID) DO NOTHING
                """,
                (
                    str(messageID), processedAt.isoformat(),
                ),
            )
            connection.commit()
            
        self.prune(referanceTime=processedAt)
        
    def get_processed_at(self, messageID: UUID) -> datetime | None:
        messageID = parse_uuid(messageID, "messageID")
        with connect_database(self.databasePath) as connection:
            row = connection.execute(
                """
                SELECT processedAt
                FROM processedMessages
                WHERE messageID = ?
                """,
                (str(messageID),),
            ).fetchone()
            
        if row is None: return None
        return parse_datetime(row["processedAt"], "processedAt")
    
    def count(self) -> int:
        with connect_database(self.databasePath) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS processedCount
                FROM processedMessages
                """
            ).fetchone()
        
        return int(row["processedCount"])
        
    def prune(self, referanceTime: datetime | None = None) -> None:
        referanceTime = (
            utcnow() if referanceTime is None 
            else parse_datetime(referanceTime, "referanceTime") 
        )
        cutoff = referanceTime - self.retentionPolicy.maxAge
        
        with connect_database(self.databasePath) as connection:
            connection.execute(
                """
                DELETE FROM processedMessages
                WHERE processedAt < ?
                """,
                (cutoff.isoformat(),),
            )
            connection.execute(
                """
                DELETE FROM processedMessages
                WHERE messageID IN (
                    SELECT messageID
                    FROM processedMessages
                    ORDER BY processedAt DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (self.retentionPolicy.maxEntries,),
            )
            connection.commit()
