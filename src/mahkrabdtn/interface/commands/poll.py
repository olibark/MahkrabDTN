from __future__ import annotations

import argparse as ap

from mahkrabdtn.interface.commands.client import build_client
from mahkrabdtn.interface.commands import polling
from mahkrabdtn.tools.interface.printing import print_json


def build_poll_payload(client, response, ack: bool) -> dict:
    payload = response.to_dict()

    if ack:
        payload["acknowledgments"] = [
            client.acknowledge_message(message.messageID).to_dict()
            for message in response.messages
        ]

    return payload


def print_poll_response(response, payload: dict, args: ap.Namespace, watching: bool) -> None:
    if args.json:
        if watching and not response.messages: return

        print_json(payload)
        return

    if not response.messages:
        if watching: return

        print("No messages.")
        return

    for message in response.messages:
        print(f"messageID: {message.messageID}")
        print(f"from: {message.senderID}")
        print(f"created: {message.created.isoformat()}")
        print(message.payload)
        if args.ack:
            print(f"acknowledged: {message.messageID}")
        print()


def poll_once(client, args: ap.Namespace, timeout_ms: int, watching: bool = False) -> None:
    response = client.poll_messages(timeout_ms=timeout_ms)
    payload = build_poll_payload(client, response, args.ack)
    print_poll_response(response, payload, args, watching)


def run_poll(args: ap.Namespace) -> int:
    timeout_ms = polling.resolve_poll_timeout_ms(args)
    polling.validate_watch_wait_ms(args)
    client = build_client(args)

    if not args.watch:
        poll_once(client, args, timeout_ms)
        return 0

    if not args.json:
        print(
            f"Polling for messages (timeout {timeout_ms} ms, wait {args.wait_ms} ms). "
            "Press Ctrl-C to stop."
        )

    try:
        while True:
            poll_once(client, args, timeout_ms, watching=True)
            polling.sleep_between_polls(args.wait_ms)
    except KeyboardInterrupt:
        if not args.json: print()

    return 0
