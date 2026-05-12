from datetime import datetime, timezone

def parse_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime): return value
    elif isinstance(value, str): timestamp = datetime.fromisoformat(value)
    else: raise TypeError(f"{field_name} must be a datetime or ISO 8601")
    if timestamp.tzinfo is None: raise ValueError(f"{field_name} must be timezone-awar")
    
    return timestamp.astimezone(timezone.utc)
    