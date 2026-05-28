from __future__ import annotations

import argparse as ap
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional
from wsgiref.simple_server import WSGIRequestHandler, make_server

from mahkrabdtn.server.app import RelayApplication
from mahkrabdtn.tools.server.server import ThreadedWSGIServer


class JsonLogFormatter(logging.Formatter):
    standardRecordFields = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        
        for key, value in record.__dict__.items():
            if key in self.standardRecordFields or key.startswith("_"): continue
            payload[key] = value
            
        return json.dumps(payload, sort_keys=True)


def create_parser() -> ap.ArgumentParser:
    parser = ap.ArgumentParser(prog="mahkrabdtn")
    parser.add_argument(
        "--log-level",
        default="INFO",
        metavar="<level>",
        help="Log level for mahkrabdtn package logs",
    )
    parser.add_argument(
        "--log-format",
        default="text",
        choices=("text", "json"),
        metavar="<format>",
        help="Log output format",
    )
    parser.add_argument(
        "--log-file",
        metavar="<file>",
        help="Write logs to a file instead of stderr",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_relay_parser(subparsers)
    return parser


def add_relay_parser(subparsers: ap._SubParsersAction[ap.ArgumentParser]) -> None:
    parser = subparsers.add_parser("relay", help="Run a DTN relay")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        metavar="<host>",
        help="Host to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        metavar="<port>",
        help="Port to bind",
    )
    parser.add_argument(
        "--poll-interval-ms",
        type=int,
        default=50,
        metavar="<ms>",
        help="Relay long-poll check interval",
    )
    parser.add_argument(
        "--database-path",
        metavar="<file>",
        help="SQLite database path for relay storage",
    )
    parser.set_defaults(func=run_relay)


def open_log_stream(logFile: str | None) -> Any:
    if not logFile:
        return sys.stderr
    
    logPath = Path(logFile)
    logPath.parent.mkdir(parents=True, exist_ok=True)
    return logPath.open("a", encoding="utf-8")


def configure_logging(args: ap.Namespace) -> None:
    logHandler = logging.StreamHandler(open_log_stream(args.log_file))
    packageLogger = logging.getLogger("mahkrabdtn")
    
    if args.log_format == "json":
        logHandler.setFormatter(JsonLogFormatter())
    else:
        logHandler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    
    packageLogger.handlers.clear()
    packageLogger.setLevel(str(args.log_level).upper())
    packageLogger.addHandler(logHandler)


def run_relay(args: ap.Namespace) -> int:
    if args.port <= 0:
        raise ValueError("port must be positive")
    if args.poll_interval_ms <= 0:
        raise ValueError("poll-interval-ms must be positive")
    
    application = RelayApplication(
        pollInterval_ms=args.poll_interval_ms,
        databasePath=args.database_path,
    )
    server = make_server(
        args.host,
        args.port,
        application,
        server_class=ThreadedWSGIServer,
        handler_class=WSGIRequestHandler,
    )
    print(f"Relay listening at http://{args.host}:{args.port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        server.server_close()
        
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    configure_logging(args)
    
    try:
        return int(args.func(args))
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
