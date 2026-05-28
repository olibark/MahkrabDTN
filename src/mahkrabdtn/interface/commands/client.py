from __future__ import annotations

import argparse as ap
import sys
from uuid import UUID

from mahkrabdtn.client import RelayNodeClient
from mahkrabdtn.tools.parsing.uuid import parse_uuid


def read_payload(value: str) -> str:
    if value == "-": return sys.stdin.read().rstrip("\n")

    return value


def build_client(args: ap.Namespace, nodeID: UUID | str | None = None) -> RelayNodeClient:
    client = RelayNodeClient.from_identity_path(
        baseURL=args.relay,
        identityPath=args.identity,
        timeout=args.timeout,
    )

    if nodeID is None: nodeID = getattr(args, "nodeID", None)
    if nodeID is None: return client

    return RelayNodeClient(
        baseURL=client.baseURL,
        nodeID=parse_uuid(nodeID, "nodeID"),
        privateKeyPem=client.privateKeyPem,
        publicKeyPem=client.publicKeyPem,
        processedMessagesStore=client.processedMessagesStore,
        timeout=client.timeout,
        retryPolicy=client.retryPolicy,
    )
