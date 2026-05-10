def parse_text(value: object, field_name: str) -> str:
    if not isinstance(value, str): raise TypeError(f"{field_name} must be string")
    if not value: raise ValueError(f"{field_name} must not be empty")
    return value