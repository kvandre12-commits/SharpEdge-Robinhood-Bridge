from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandSpec:
    name: str
    category: str
    support_tier: str
    route: str
    summary: str
    aliases: tuple[str, ...] = ()
    approval_policy: str = "not_applicable"
    notes: tuple[str, ...] = ()

    def matches(self, candidate: str) -> bool:
        normalized = (candidate or "").strip().lower()
        return normalized == self.name or normalized in self.aliases


@dataclass
class CommandPlan:
    candidate: str
    normalized: str
    matched: bool
    actual_command_name: str
    category: str
    support_tier: str
    route: str
    approval_policy: str
    summary: str
    notes: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
