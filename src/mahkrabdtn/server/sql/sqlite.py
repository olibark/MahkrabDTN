import sqlite3
from pathlib import Path


def ensure_parent_directory(databasePath: str | Path) -> None:
    if databasePath == ":memory:": return
    Path(databasePath).parent.mkdir(parents=True, exist_ok=True)


def connect_database(databasePath: str | Path) -> sqlite3.Connection:
    ensure_parent_directory(databasePath)
    connection = sqlite3.connect(str(databasePath), timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    
    return connection
