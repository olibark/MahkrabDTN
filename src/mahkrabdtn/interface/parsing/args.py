from __future__ import annotations

import argparse as ap
from pathlib import Path

from mahkrabdtn.helpers.environ import identity_path_from_env, relay_url_from_env


def add_json_arg(parser: ap.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )


def add_client_args(parser: ap.ArgumentParser) -> None:
    parser.add_argument(
        "--relay",
        default=relay_url_from_env(),
        metavar="<url>",
        help=f"Relay URL (default: {relay_url_from_env()})",
    )
    parser.add_argument(
        "--identity",
        type=Path,
        default=identity_path_from_env(),
        metavar="<file>",
        help=f"Node identity file (default: {identity_path_from_env()})",
    )
    parser.add_argument(
        "--node-id",
        dest="nodeID",
        metavar="<node-id>",
        help="Use this node ID instead of the saved identity node ID",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        metavar="<seconds>",
        help="HTTP timeout in seconds (default: 5.0)",
    )
