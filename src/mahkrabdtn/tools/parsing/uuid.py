from uuid import UUID

def parse_uuid(value: object, field_name: str) -> UUID:
    if isinstance(value, UUID): return value
    if isinstance(value, str): return UUID(value)
    raise TypeError(f"{field_name} must be a UUID or UUID string")
