from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import CommandExecutionResult
from .router import plan_command
from .watchlists import create_watchlist

_HANDLER_MAP = {
    "create_watchlist": create_watchlist,
}


def run_command(
    candidate: str,
    payload: dict[str, Any] | None = None,
    *,
    base_dir: Path | None = None,
) -> CommandExecutionResult:
    payload = payload or {}
    plan = plan_command(candidate, payload)
    if not plan.matched:
        return CommandExecutionResult(
            status="blocked",
            executed=False,
            command_name=candidate,
            route=plan.route,
            summary="Command is not modeled yet.",
            notes=plan.notes,
            payload=payload,
            result={},
        )

    if not plan.handler_name:
        return CommandExecutionResult(
            status="not_implemented",
            executed=False,
            command_name=plan.actual_command_name,
            route=plan.route,
            summary="Command has a policy definition but no local handler yet.",
            notes=plan.notes,
            payload=payload,
            result={},
        )

    handler = _HANDLER_MAP[plan.handler_name]
    try:
        result = handler(payload, base_dir=base_dir)
    except ValueError as exc:
        return CommandExecutionResult(
            status="invalid_payload",
            executed=False,
            command_name=plan.actual_command_name,
            route=plan.route,
            summary=str(exc),
            notes=plan.notes,
            payload=payload,
            result={},
        )

    notes = list(plan.notes)
    notes.extend(result.get("notes", []))
    return CommandExecutionResult(
        status=result.get("status", "ok"),
        executed=True,
        command_name=plan.actual_command_name,
        route=plan.route,
        summary=plan.summary,
        notes=notes,
        payload=payload,
        result=result,
    )
