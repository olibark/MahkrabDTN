from __future__ import annotations

import argparse as ap
from wsgiref.simple_server import WSGIRequestHandler, make_server

from mahkrabdtn.server.app import RelayApplication
from mahkrabdtn.tools.interface.printing import print_success
from mahkrabdtn.tools.server.server import ThreadedWSGIServer


def run_serve(args: ap.Namespace) -> int:
    if args.port <= 0:
        raise ValueError("port must be positive")
    if args.pollInterval_ms <= 0:
        raise ValueError("poll-interval-ms must be positive")

    application = RelayApplication(
        pollInterval_ms=args.pollInterval_ms,
        databasePath=args.databasePath,
    )
    server = make_server(
        args.host,
        args.port,
        application,
        server_class=ThreadedWSGIServer,
        handler_class=WSGIRequestHandler,
    )
    print_success(f"Relay listening at http://{args.host}:{args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        server.server_close()

    return 0
