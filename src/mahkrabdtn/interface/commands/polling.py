from __future__ import annotations

import argparse as ap
from time import sleep


DEFAULT_WATCH_TIMEOUT_MS = 4000
DEFAULT_WATCH_WAIT_MS = 1000


def resolve_poll_timeout_ms(args: ap.Namespace) -> int:
    if args.timeout_ms is None:
        if args.watch: return DEFAULT_WATCH_TIMEOUT_MS
        return 0

    if args.timeout_ms < 0: raise ValueError("timeout-ms must be positive")

    return args.timeout_ms


def validate_watch_wait_ms(args: ap.Namespace) -> None:
    if args.wait_ms < 0: raise ValueError("wait-ms must be positive")


def sleep_between_polls(wait_ms: int) -> None:
    if wait_ms == 0: return

    sleep(wait_ms / 1000)
