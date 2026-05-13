import sqlite3
from pathlib import Path

from mahkrabdtn.helpers.resolve import resolve_processed_messages_path


def connect_database(databasePath: str | Path) -> sqlite3.Connection:
    path = resolve_processed_messages_path(databasePath)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    
    return connection
    
