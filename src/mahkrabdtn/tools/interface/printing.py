import json
import sys
from typing import Any

from mahkrabdtn.interface.constants import Colours


def print_success(message: str) -> None:
    print(f"{Colours.MAGENTA}[MAHKRAB-DTN] - {Colours.GREEN}{message}{Colours.ENDC}")


def print_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def print_error(message: str) -> None:
    print(
        f"\n{Colours.MAGENTA}[MAHKRAB-DTN] - {Colours.RED}Error:{Colours.ENDC} {message}\n",
        file=sys.stderr,
    )
