from __future__ import annotations

import argparse as ap

from mahkrabdtn.interface.commands.client import build_client
from mahkrabdtn.tools.interface.printing import print_json, print_success


def run_register(args: ap.Namespace) -> int:
    client = build_client(args)
    registration = client.register()
    payload = registration.to_dict()

    if args.json:
        print_json(payload)
        return 0

    print_success(f"Registered node {payload['nodeID']}")
    print(f"lastSeen: {payload['lastSeen']}")
    return 0
