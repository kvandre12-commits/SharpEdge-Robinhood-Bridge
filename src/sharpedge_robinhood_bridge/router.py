from __future__ import annotations

from typing import Any

from .catalog import find_command_spec
from .models import CommandPlan


def plan_command(candidate: str, payload: dict[str, Any] | None = None) -> CommandPlan:
    normalized = (candidate or "").strip().lower()
    payload = payload or {}
    spec = find_command_spec(normalized)
    if spec is None:
        return CommandPlan(
            candidate=candidate,
            normalized=normalized,
            matched=False,
            actual_command_name="",
            category="unknown",
            support_tier="unknown",
            route="unknown",
            approval_policy="unknown",
            handler_name="",
            summary="No registry match yet.",
            notes=[
                "Add a command spec before wiring logic.",
                "Do not pretend unknown commands are source-verified.",
            ],
            payload=payload,
        )

    notes = list(spec.notes)
    if spec.route == "public_mcp_read":
        notes.append("Read/research command. No live-order authority implied.")
    if spec.route == "chatgpt_delegate":
        notes.append("Route through approval-gated delegate flow, not direct autonomous submission.")
    if spec.route == "custom_logic_required":
        notes.append("This repo is the right place to implement new handler logic for this command.")
    if spec.route == "custom_logic_local":
        notes.append("This command is handled locally by SharpEdge Robinhood Bridge custom logic.")

    return CommandPlan(
        candidate=candidate,
        normalized=normalized,
        matched=True,
        actual_command_name=spec.name,
        category=spec.category,
        support_tier=spec.support_tier,
        route=spec.route,
        approval_policy=spec.approval_policy,
        handler_name=spec.handler_name,
        summary=spec.summary,
        notes=notes,
        payload=payload,
    )
