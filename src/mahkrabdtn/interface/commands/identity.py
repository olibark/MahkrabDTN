from __future__ import annotations

import argparse as ap
from pathlib import Path

from mahkrabdtn.client import RelayNodeClient, create_node_id
from mahkrabdtn.interface.constants import DEFAULT_RELAY_URL
from mahkrabdtn.tools.interface.printing import print_json, print_success
from mahkrabdtn.tools.parsing.uuid import parse_uuid


def set_identity_node_id(identityPath: Path, nodeID: object, force: bool = False) -> None:
    identityPath.parent.mkdir(parents=True, exist_ok=True)
    parsedNodeID = parse_uuid(nodeID, "nodeID")

    if identityPath.exists():
        currentNodeID = parse_uuid(identityPath.read_text(encoding="utf-8").strip(), "nodeID")
        if currentNodeID != parsedNodeID and not force:
            raise ValueError(
                f"identity already contains nodeID {currentNodeID}; use --force to replace it"
            )

    identityPath.write_text(str(parsedNodeID), encoding="utf-8")


def build_identity_payload(identityPath: Path) -> dict[str, str]:
    privateKeyPath = identityPath.with_suffix(".privkey.pem")
    processedMessagesPath = identityPath.with_suffix(".processedmessages.sqlite3")
    
    return {
        "nodeID": str(create_node_id(identityPath)),
        "identityPath": str(identityPath),
        "privateKeyPath": str(privateKeyPath),
        "processedMessagesPath": str(processedMessagesPath),
    }


def run_identity(args: ap.Namespace) -> int:
    if args.nodeID is not None:
        set_identity_node_id(args.identity, args.nodeID, args.force)

    client = RelayNodeClient.from_identity_path(
        baseURL=DEFAULT_RELAY_URL,
        identityPath=args.identity,
    )
    payload = build_identity_payload(args.identity)
    payload["publicKey"] = client.publicKeyPem

    if args.json:
        print_json(payload)
        return 0

    if args.nodeID is not None:
        print_success(f"Set node identity {payload['nodeID']}")

    print(f"nodeID: {payload['nodeID']}")
    print(f"identity: {payload['identityPath']}")
    print(f"privateKey: {payload['privateKeyPath']}")
    print(f"processedMessages: {payload['processedMessagesPath']}")
    
    return 0
