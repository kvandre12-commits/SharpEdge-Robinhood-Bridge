from __future__ import annotations

import argparse
import json
from typing import Any

from .executor import run_command
from .router import plan_command


def _parse_payload(raw_payload: str) -> dict[str, Any]:
    text = (raw_payload or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Payload must decode to a JSON object.")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sharpedge-robinhood-bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("capability")

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("capability")
    plan_parser.add_argument("--payload", default="")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("capability")
    run_parser.add_argument("--payload", default="")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = _parse_payload(getattr(args, "payload", ""))
    if args.command == "run":
        result = run_command(args.capability, payload)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return

    plan = plan_command(args.capability, payload)
    print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
