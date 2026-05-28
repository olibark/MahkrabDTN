from __future__ import annotations

import argparse as ap

from mahkrabdtn.interface.commands.client import build_client, read_payload
from mahkrabdtn.tools.interface.printing import print_json, print_success
from mahkrabdtn.tools.parsing.time import parse_datetime
from mahkrabdtn.tools.parsing.uuid import parse_uuid


def resolve_send_args(args: ap.Namespace) -> tuple[object | None, object, str]:
    if args.payload is None:
        return None, args.nodeOrRecipientID, args.recipientOrPayload

    return args.nodeOrRecipientID, args.recipientOrPayload, args.payload


def run_send(args: ap.Namespace) -> int:
    nodeID, recipientID, payloadText = resolve_send_args(args)
    client = build_client(args, nodeID=nodeID)
    recipientID = parse_uuid(recipientID, "recipientID")
    recipientPublicKey = None

    if args.recipientPublicKeyFile is not None:
        recipientPublicKey = args.recipientPublicKeyFile.read_text(encoding="utf-8")

    expiresAt = parse_datetime(args.expires, "expires") if args.expires else None
    receipt = client.send_message(
        recipientID=recipientID,
        payload=read_payload(payloadText),
        recipientPublicKey=recipientPublicKey,
        expiresAt=expiresAt,
    )
    outputPayload = receipt.to_dict()

    if args.json:
        print_json(outputPayload)
        return 0

    print_success(f"Sent message {outputPayload['messageID']}")
    print(f"from: {client.nodeID}")
    print(f"to: {recipientID}")
    print(f"state: {outputPayload['state']}")
    return 0
