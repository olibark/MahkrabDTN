from pathlib import Path


def resolve_processed_messages_path(identityPath: str | Path) -> Path:
    return Path(identityPath).with_suffix(".processedmessages.sqlite3")