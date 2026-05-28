from pathlib import Path


def resolve_processed_messages_path(identityPath: str | Path) -> Path:
    return Path(identityPath).with_suffix(".processedmessages.sqlite3")


def resolve_aliases_path(identityPath: str | Path) -> Path:
    return Path(identityPath).with_suffix(".aliases.json")
