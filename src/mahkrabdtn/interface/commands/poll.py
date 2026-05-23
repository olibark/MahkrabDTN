from __future__ import annotations

import argparse as ap

from mahkrabdtn.interface.commands.client import build_client
from mahkrabdtn.tools.interface.printing import print_json


def run_poll(args: ap.Namespace) -> int:
    client = build_client(args)
    response = client.poll_messages(timeout_ms=args.timeout_ms)
    payload = response.to_dict()

    if args.ack:
        payload["acknowledgments"] = [
            client.acknowledge_message(message.messageID).to_dict()
            for message in response.messages
        ]

    if args.json:
        print_json(payload)
        return 0

    if not response.messages:
        print("No messages.")
        return 0

    for message in response.messages:
        print(f"messageID: {message.messageID}")
        print(f"from: {message.senderID}")
        print(f"created: {message.created.isoformat()}")
        print(message.payload)
        if args.ack:
            print(f"acknowledged: {message.messageID}")
        print()

    return 0
