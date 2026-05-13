from pathlib import Path
from dataclasses import dataclass, field

from mahkrabdtn.client.policys import ProcessedMessageRetentionPolicy
from mahkrabdtn.tools.database.connect import connect_database
from mahkrabdtn.helpers.resolve import resolve_processed_messages_path


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
        self.databasePath.parent.mkdir(parent=True, exist_ok=True)
        if not isinstance(self.retentionPolicy, ProcessedMessageRetentionPolicy): 
            raise TypeError("retentionPolicy must be of type ProcessedMessageRetentionPolicy")
        self.initialize_schema()
        
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