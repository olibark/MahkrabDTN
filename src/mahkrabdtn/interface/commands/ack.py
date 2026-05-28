from __future__ import annotations

import argparse as ap

from mahkrabdtn.interface.commands.client import build_client
from mahkrabdtn.tools.interface.printing import print_json, print_success
from mahkrabdtn.tools.parsing.uuid import parse_uuid


def run_ack(args: ap.Namespace) -> int:
    client = build_client(args)
    receipt = client.acknowledge_message(parse_uuid(args.messageID, "messageID"))
    payload = receipt.to_dict()

    if args.json:
        print_json(payload)
        return 0

    print_success(f"Acknowledged message {payload['messageID']}")
    print(f"state: {payload['state']}")
    return 0
