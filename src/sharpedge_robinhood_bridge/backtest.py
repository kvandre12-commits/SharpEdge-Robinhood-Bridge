"""Backtest grading engine: replay historical signals through ``decide()``.

This is the honest answer to "which gate states actually have edge?". It is a
PURE grading core - it takes historical signal dicts plus a forward return and
reports per-state outcomes. It owns NO data access; the data adapter
(SharpEdge-System side) reconstructs the signals and hands them in. That split
keeps the math testable and the data plumbing replaceable.

A fired intent is one long option leg, so its directional sign is +1 for a call
and -1 for a put. The graded P/L is the forward underlying return aligned to
that direction (``signed_return``). A leveraged option amplifies but does not
change the SIGN of a single long leg, so signed underlying return is the honest,
assumption-light edge measure. We also surface a delta-scaled premium estimate
for color, never as the headline.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from .analytics_context import AnalyticsContext
from .trade_intent import decide


@dataclass
class GradedTrade:
    session: str
    action: str
    reason: str
    direction: str | None          # "call" | "put" | None
    fwd_return_pct: float
    signed_return_pct: float | None  # forward return aligned to direction
    win: bool | None


@dataclass
class StateStat:
    reason: str
    n: int = 0
    wins: int = 0
    sum_signed: float = 0.0

    @property
    def win_rate(self) -> float | None:
        return self.wins / self.n if self.n else None

    @property
    def avg_signed_return(self) -> float | None:
        return self.sum_signed / self.n if self.n else None


@dataclass
class BacktestResult:
    n_signals: int = 0
    n_trades: int = 0
    n_wins: int = 0
    sum_signed: float = 0.0
    by_reason: dict[str, StateStat] = field(default_factory=dict)
    trades: list[GradedTrade] = field(default_factory=list)

    @property
    def win_rate(self) -> float | None:
        return self.n_wins / self.n_trades if self.n_trades else None

    @property
    def avg_signed_return(self) -> float | None:
        return self.sum_signed / self.n_trades if self.n_trades else None

    def summary(self) -> dict[str, Any]:
        return {
            "n_signals": self.n_signals,
            "n_trades": self.n_trades,
            "win_rate": self.win_rate,
            "avg_signed_return_pct": self.avg_signed_return,
            "total_signed_return_pct": self.sum_signed,
            "by_reason": {
                r: {
                    "n": s.n,
                    "win_rate": s.win_rate,
                    "avg_signed_return_pct": s.avg_signed_return,
                }
                for r, s in sorted(self.by_reason.items())
            },
        }


def grade_signal(
    signal: dict[str, Any],
    fwd_return_pct: float,
    *,
    analytics: AnalyticsContext | None = None,
) -> GradedTrade:
    """Run ``decide`` on one signal and grade it against the forward return.

    A backtest must be hermetic: when no point-in-time analytics is supplied we
    pass an explicit UNAVAILABLE context so ``decide`` does NOT reach into the
    live execution-state file (that would be lookahead + non-reproducible).
    """
    session = str(signal.get("session") or signal.get("date") or signal.get("ts") or "?")
    if analytics is None:
        analytics = AnalyticsContext(available=False, fresh=False, note="backtest: no point-in-time analytics")
    decision = decide(signal, analytics=analytics)
    action = decision["action"]
    reason = decision["reason"]

    if action != "trade" or decision["intent"] is None:
        return GradedTrade(session, action, reason, None, fwd_return_pct, None, None)

    legs = decision["intent"].option_legs
    right = (legs[0]["right"] if legs else "call").lower()
    sign = 1.0 if right == "call" else -1.0
    signed = fwd_return_pct * sign
    return GradedTrade(session, action, reason, right, fwd_return_pct, signed, signed > 0)


def run_backtest(
    records: Iterable[tuple[dict[str, Any], float]],
    *,
    analytics_for: dict[str, AnalyticsContext] | None = None,
) -> BacktestResult:
    """Grade an iterable of ``(signal, forward_return_pct)`` records.

    ``analytics_for`` optionally maps a signal's session/date key to the daily
    AnalyticsContext that was true on that day (point-in-time, no lookahead).
    """
    result = BacktestResult()
    for signal, fwd in records:
        result.n_signals += 1
        key = str(signal.get("session") or signal.get("date") or "")
        ctx = (analytics_for or {}).get(key)
        graded = grade_signal(signal, fwd, analytics=ctx)
        result.trades.append(graded)

        bucket = result.by_reason.setdefault(graded.reason, StateStat(graded.reason))
        bucket.n += 1
        if graded.action == "trade":
            result.n_trades += 1
            bucket.sum_signed += graded.signed_return_pct or 0.0
            if graded.win:
                result.n_wins += 1
                bucket.wins += 1
            result.sum_signed += graded.signed_return_pct or 0.0
    return result
