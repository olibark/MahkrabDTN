import os
from pathlib import Path

from mahkrabdtn.interface.constants import DEFAULT_RELAY_URL, DEFAULT_IDENTITY_PATH


def relay_url_from_env() -> str:
    return os.environ.get("MAHKRABDTN_RELAY", DEFAULT_RELAY_URL)


def identity_path_from_env() -> Path:
    return Path(
        os.environ.get("MAHKRABDTN_IDENTITY", str(DEFAULT_IDENTITY_PATH))
    ).expanduser()
