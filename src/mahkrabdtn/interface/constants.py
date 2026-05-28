from pathlib import Path

DEFAULT_RELAY_URL = "https://relay.mahkrab.com"
DEFAULT_IDENTITY_PATH = Path("~/.mahkrabdtn/node.id").expanduser()


class Colours:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    ENDC = "\033[0m"
