#!/usr/bin/env python3
"""
⟦APΩ:Σ⟧ APO Canon CLI
"""

import argparse
import json
import sys

import httpx


def _request(base_url: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    with httpx.Client(timeout=10.0) as client:
        if method == "GET":
            resp = client.get(url)
        else:
            resp = client.post(url, json=body or {})
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="⟦APΩ:Σ⟧ APO Canon CLI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="BalanceHub API base URL")

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("canon-validate")
    sub.add_parser("canon-proof")
    sub.add_parser("canon-coverage")
    sub.add_parser("memory-status")
    sub.add_parser("memory-sync")

    args = parser.parse_args()

    if args.cmd == "canon-validate":
        out = _request(args.base_url, "GET", "/canon/validate")
    elif args.cmd == "canon-proof":
        out = _request(args.base_url, "GET", "/canon/proof")
    elif args.cmd == "canon-coverage":
        out = _request(args.base_url, "GET", "/canon/coverage")
    elif args.cmd == "memory-status":
        out = _request(args.base_url, "GET", "/canon/memory/status")
    elif args.cmd == "memory-sync":
        out = _request(args.base_url, "POST", "/canon/memory/sync")
    else:
        print("unknown command", file=sys.stderr)
        return 2

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
