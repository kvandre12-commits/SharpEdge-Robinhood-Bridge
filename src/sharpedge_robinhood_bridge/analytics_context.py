"""Bridge from SharpEdge's daily analytics layer into live execution.

Reads the published `execution_state_daily.csv` artifact and exposes a small,
freshness-guarded context dict. Design rule (see sharpedge skill stack):

    Analytics may TIGHTEN execution (veto / annotate / confidence) but never
    LOOSEN it, and stale data is IGNORED WITH A NOTE rather than silently
    trusted. This surfaces pipeline-freshness problems instead of hiding them.

The daily state's `final_bias` has historically been non-directional
(WHIP_WAIT / BALANCED_SMALL), so its real value to execution is the
trend-vs-range probability split and a freshness/agreement check — not a
"go" signal.
"""

from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(
    os.path.expanduser("~/SharpEdge-System/outputs/execution_state_daily.csv")
)
# A daily artifact older than this is not trusted as live confirmation.
DEFAULT_MAX_AGE_DAYS = 5


@dataclass
class AnalyticsContext:
    available: bool
    fresh: bool
    note: str
    symbol: str = "SPY"
    session_date: str | None = None
    age_days: int | None = None
    prob_trend: float | None = None
    prob_range: float | None = None
    final_bias: str | None = None
    dealer_state: str | None = None
    execution_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def load_execution_state(
    path: Path | None = None,
    *,
    symbol: str = "SPY",
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    today: date | None = None,
) -> AnalyticsContext:
    """Load the latest daily execution-state row for ``symbol``.

    Always returns an AnalyticsContext. ``available`` is False if the artifact
    is missing/empty/has no matching symbol; ``fresh`` is False if it is older
    than ``max_age_days``. Never raises on bad data (fail-soft).
    """
    path = path or DEFAULT_PATH
    today = today or date.today()

    if not path.exists():
        return AnalyticsContext(False, False, f"no analytics artifact at {path}")

    try:
        rows = [
            r
            for r in csv.DictReader(path.open("r", encoding="utf-8", newline=""))
            if (r.get("symbol") or "").upper() == symbol.upper()
        ]
    except (OSError, csv.Error) as exc:
        return AnalyticsContext(False, False, f"unreadable analytics artifact: {exc}")

    if not rows:
        return AnalyticsContext(False, False, f"no {symbol} rows in analytics artifact")

    row = rows[-1]
    sdate = _parse_date(row.get("session_date"))
    age = (today - sdate).days if sdate else None
    fresh = age is not None and age <= max_age_days
    note = (
        f"daily analytics fresh (age {age}d)"
        if fresh
        else f"daily analytics STALE (age {age}d > {max_age_days}d) - not used as confirmation"
        if age is not None
        else "daily analytics has no usable session_date"
    )

    return AnalyticsContext(
        available=True,
        fresh=fresh,
        note=note,
        symbol=symbol.upper(),
        session_date=row.get("session_date"),
        age_days=age,
        prob_trend=_as_float(row.get("prob_trend_fused")),
        prob_range=_as_float(row.get("prob_range_fused")),
        final_bias=row.get("final_bias"),
        dealer_state=row.get("dealer_state_hint"),
        execution_score=_as_float(row.get("execution_score")),
    )
