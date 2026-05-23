from __future__ import annotations

import json
from typing import Optional
from urllib import error

from mahkrabdtn.client import RelayClientError
from mahkrabdtn.interface.parsing.parser import create_parser
from mahkrabdtn.tools.interface.printing import print_error


def main(argv: Optional[list[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    try:
        return int(args.func(args))
    except (
        OSError,
        RelayClientError,
        ValueError,
        TypeError,
        error.URLError,
        json.JSONDecodeError,
    ) as caughtError:
        print_error(str(caughtError))
        return 2
