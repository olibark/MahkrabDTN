from __future__ import annotations

import argparse as ap
import json
from urllib import request

from mahkrabdtn.tools.interface.printing import print_json, print_success


def run_health(args: ap.Namespace) -> int:
    relay = args.relay.rstrip("/")
    httpRequest = request.Request(f"{relay}/healthsz", method="GET")

    with request.urlopen(httpRequest, timeout=args.timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if args.json:
        print_json(payload)
        return 0

    print_success(f"Relay health: {payload['status']}")
    print(f"storageBackend: {payload['storageBackend']}")
    print(f"serverTime: {payload['serverTime']}")
    return 0
