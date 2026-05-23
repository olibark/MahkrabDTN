from __future__ import annotations

import argparse as ap
from pathlib import Path

from mahkrabdtn.helpers.environ import identity_path_from_env, relay_url_from_env
from mahkrabdtn.helpers.version import get_version
from mahkrabdtn.interface.commands import (
    run_ack,
    run_health,
    run_identity,
    run_poll,
    run_register,
    run_send,
    run_serve,
)
from mahkrabdtn.interface.parsing.args import add_client_args, add_json_arg


def create_parser() -> ap.ArgumentParser:
    parser = ap.ArgumentParser(
        prog="mkdtn",
        epilog=(
            "Commands: serve (run a relay), identity (create or show node identity), "
            "register (register with relay), send (send a message), poll (receive messages), "
            "ack (acknowledge a message), health (check relay health)."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"mahkrabdtn {get_version()}",
        help="Show program version",
    )

    subparsers = parser.add_subparsers(dest="command")
    add_serve_parser(subparsers)
    add_identity_parser(subparsers)
    add_register_parser(subparsers)
    add_send_parser(subparsers)
    add_poll_parser(subparsers)
    add_ack_parser(subparsers)
    add_health_parser(subparsers)
    return parser


def add_serve_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("serve", help="Run a local DTN relay")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        metavar="<host>",
        help="Host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        metavar="<port>",
        help="Port to bind (default: 8000)",
    )
    parser.add_argument(
        "--poll-interval-ms",
        dest="pollInterval_ms",
        type=int,
        default=50,
        metavar="<ms>",
        help="Relay long-poll check interval (default: 50)",
    )
    parser.add_argument(
        "--database-path",
        dest="databasePath",
        metavar="<file>",
        help="SQLite database path for relay storage",
    )
    parser.set_defaults(func=run_serve)


def add_identity_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("identity", help="Create, set, or show the local node identity")
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
        help="Set the saved node ID for this device",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing saved node ID when used with --node-id",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run_identity)


def add_register_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("register", help="Register this node with a relay")
    add_client_args(parser)
    add_json_arg(parser)
    parser.set_defaults(func=run_register)


def add_send_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("send", help="Send an encrypted message")
    add_client_args(parser)
    parser.add_argument(
        "nodeOrRecipientID",
        metavar="<node-id|recipient-id>",
        help="Recipient node UUID, or sender node UUID when recipient and payload are also given",
    )
    parser.add_argument(
        "recipientOrPayload",
        metavar="<recipient-id|payload>",
        help="Message payload, or recipient UUID when a sender node UUID is given",
    )
    parser.add_argument(
        "payload",
        nargs="?",
        metavar="<payload>",
        help="Message text, or '-' to read from stdin",
    )
    parser.add_argument(
        "--recipient-public-key-file",
        dest="recipientPublicKeyFile",
        type=Path,
        metavar="<file>",
        help="Use a PEM public key file instead of resolving the recipient through the relay",
    )
    parser.add_argument(
        "--expires",
        metavar="<iso-datetime>",
        help="Optional timezone-aware ISO 8601 expiry time",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run_send)


def add_poll_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("poll", help="Poll the relay for messages")
    add_client_args(parser)
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=0,
        metavar="<ms>",
        help="Long-poll timeout in milliseconds (default: 0)",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Acknowledge each delivered message after printing it",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run_poll)


def add_ack_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("ack", help="Acknowledge a delivered message")
    add_client_args(parser)
    parser.add_argument("messageID", metavar="<message-id>", help="Message UUID to acknowledge")
    add_json_arg(parser)
    parser.set_defaults(func=run_ack)


def add_health_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("health", help="Check relay health")
    parser.add_argument(
        "relay",
        nargs="?",
        default=relay_url_from_env(),
        metavar="<url>",
        help=f"Relay URL (default: {relay_url_from_env()})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        metavar="<seconds>",
        help="HTTP timeout in seconds (default: 5.0)",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run_health)
