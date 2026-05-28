from __future__ import annotations

import argparse as ap

from mahkrabdtn.client.store.aliases import NodeAliasBook
from mahkrabdtn.helpers.resolve import resolve_aliases_path
from mahkrabdtn.interface.commands.client import build_client
from mahkrabdtn.interface.tui import MessengerApp


def run_tui(args: ap.Namespace) -> int:
    if args.pollTimeout_ms < 0: raise ValueError("poll-time-ms must be positive")
    if args.pollWait_ms < 0: raise ValueError("wait-ms must be positive")

    client = build_client(args)
    aliasPath = args.aliasPath or resolve_aliases_path(args.identity)
    aliases = NodeAliasBook.from_path(aliasPath)
    app = MessengerApp(
        client=client,
        aliases=aliases,
        pollTimeout_ms=args.pollTimeout_ms,
        pollWait_ms=args.pollWait_ms,
        autoRegister=not args.noAutoRegister,
        autoAck=not args.noAutoAck,
    )
    app.run()
    return 0
