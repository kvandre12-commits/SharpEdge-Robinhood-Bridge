"""Trade-intent pipeline: signal -> structured order -> risk gate -> delegation.

This is the missing link between SharpEdge strategy signals and an agentic
trade. It does NOT submit orders. By governance (Tier C, active_trading_write)
every order routes through chatgpt_delegate with operator_confirm_required.

Flow:
    build_intent(signal)        # strategy -> structured OrderIntent
      -> risk_check(intent)     # tiny-size + notional + kill-switch guardrails
      -> plan_command(...)      # bridge policy brain classifies (Tier C gate)
      -> delegation_payload     # what the ChatGPT Robinhood connector executes
      -> status: awaiting_operator_confirm   # the human gate. No silent submit.

The agent may run everything up to the gate autonomously. The live submit is
performed by the ChatGPT Robinhood connector AFTER the operator confirms.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .analytics_context import AnalyticsContext, load_execution_state
from .option_leg import build_option_leg
from .router import plan_command

# --------------------------------------------------------------------------
# Risk guardrails (tiny live size). Tunable, but conservative by default.
# --------------------------------------------------------------------------
KILL_SWITCH = Path(os.path.expanduser("~/.sharpedge_kill"))
ALLOWED_SYMBOLS = {"SPY"}
MAX_EQUITY_QTY = 1            # 1 share max while testing the live path
MAX_OPTION_CONTRACTS = 1      # 1 contract max
MAX_NOTIONAL_USD = 1500.0     # hard ceiling on a single order's notional
ALLOWED_SIDES = {"buy", "sell"}
ALLOWED_TYPES = {"market", "limit"}


@dataclass
class OrderIntent:
    symbol: str
    side: str                 # buy | sell
    quantity: int
    order_type: str           # market | limit
    limit_price: float | None = None
    asset: str = "equity"     # equity | option
    option_legs: list[dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    source_signal: dict[str, Any] = field(default_factory=dict)

    def notional(self) -> float:
        ref = self.limit_price or float(self.source_signal.get("spot", 0) or 0)
        return ref * self.quantity * (100 if self.asset == "option" else 1)


@dataclass
class RiskResult:
    ok: bool
    blocks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def risk_check(intent: OrderIntent) -> RiskResult:
    blocks: list[str] = []
    notes: list[str] = []

    if KILL_SWITCH.exists():
        blocks.append(f"KILL SWITCH active ({KILL_SWITCH}) - all trading halted.")

    if intent.symbol.upper() not in ALLOWED_SYMBOLS:
        blocks.append(f"Symbol {intent.symbol} not in allow-list {sorted(ALLOWED_SYMBOLS)}.")
    if intent.side not in ALLOWED_SIDES:
        blocks.append(f"Side '{intent.side}' invalid.")
    if intent.order_type not in ALLOWED_TYPES:
        blocks.append(f"Order type '{intent.order_type}' invalid.")
    if intent.order_type == "limit" and not intent.limit_price:
        blocks.append("Limit order requires a limit_price.")

    if intent.asset == "equity" and intent.quantity > MAX_EQUITY_QTY:
        blocks.append(f"Equity qty {intent.quantity} exceeds tiny-size cap {MAX_EQUITY_QTY}.")
    if intent.asset == "option" and intent.quantity > MAX_OPTION_CONTRACTS:
        blocks.append(f"Option contracts {intent.quantity} exceeds cap {MAX_OPTION_CONTRACTS}.")
    if intent.quantity < 1:
        blocks.append("Quantity must be >= 1.")

    notional = intent.notional()
    if notional > MAX_NOTIONAL_USD:
        blocks.append(f"Notional ${notional:.2f} exceeds ceiling ${MAX_NOTIONAL_USD:.2f}.")
    else:
        notes.append(f"Notional ${notional:.2f} within ${MAX_NOTIONAL_USD:.2f} ceiling.")

    return RiskResult(ok=not blocks, blocks=blocks, notes=notes)


def build_delegation_payload(intent: OrderIntent) -> dict[str, Any]:
    """Shape what the ChatGPT Robinhood connector would execute."""
    legs = intent.option_legs if intent.asset == "option" else []
    return {
        "symbol": intent.symbol.upper(),
        "asset": intent.asset,
        "side": intent.side,
        "quantity": intent.quantity,
        "order_type": intent.order_type,
        "limit_price": intent.limit_price,
        "time_in_force": "day",
        "option_legs": legs,
    }


def prepare_trade(intent: OrderIntent, *, command: str = "order_submit") -> dict[str, Any]:
    """Run the full pipeline up to (but not through) the operator gate."""
    risk = risk_check(intent)
    plan = plan_command(command, build_delegation_payload(intent))

    gated = plan.approval_policy == "operator_confirm_required"
    if not risk.ok:
        status = "blocked_by_risk"
    elif not plan.matched:
        status = "blocked_unmodeled_command"
    elif gated:
        status = "awaiting_operator_confirm"
    else:
        status = "ready"

    return {
        "schema": "sharpedge.trade_intent.v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "command": plan.actual_command_name or command,
        "route": plan.route,
        "approval_policy": plan.approval_policy,
        "risk": asdict(risk),
        "intent": asdict(intent),
        "delegation_payload": build_delegation_payload(intent),
        "rationale": intent.rationale,
        "operator_action": (
            "TAP CONFIRM to release this to the ChatGPT Robinhood connector."
            if status == "awaiting_operator_confirm"
            else "Resolve blocks before this can proceed."
        ),
        "notes": list(plan.notes),
    }


# --------------------------------------------------------------------------
# Deterministic decision rule: signal.json -> OrderIntent or stand-down.
# Conservative on purpose. Most days = stand down. Honest > busy.
# --------------------------------------------------------------------------
WALL_PROXIMITY_PCT = 0.20   # within 0.2% of a wall = no fresh entry
MIN_VOL_MULT = 1.2          # need volume confirmation
MIN_VS_VWAP = 0.05          # need to be clearly on one side of VWAP
MIN_MOM = 0.05              # need real 15m thrust
# Daily analytics may only TIGHTEN execution. A fresh range-day read whose
# range probability exceeds trend probability by this margin vetoes a runner long.
RANGE_VETO_MARGIN = 0.20
# Symmetric guard for the fade: a fresh TREND-dominant read vetoes a fade (the
# 'edge' is more likely to break than revert when the daily regime favors trend).
TREND_VETO_MARGIN = 0.20
# Fade trigger: price within this % of a wall counts as 'at the edge' to fade.
FADE_EDGE_PCT = 0.30
# Pay up to this fraction over the model premium to get a marketable buy fill.
ENTRY_LIMIT_MARKUP = 0.02


def _load_analytics(signal, analytics):
    if analytics is None:
        analytics = load_execution_state(symbol=signal.get("symbol", "SPY"))
    return analytics


def _range_favored(a: AnalyticsContext) -> bool:
    """Fresh daily regime leans RANGE by the veto margin (kills a runner long)."""
    return (
        a.fresh
        and a.prob_trend is not None
        and a.prob_range is not None
        and (a.prob_range - a.prob_trend) > RANGE_VETO_MARGIN
    )


def _trend_favored(a: AnalyticsContext) -> bool:
    """Fresh daily regime leans TREND by the veto margin (kills a fade)."""
    return (
        a.fresh
        and a.prob_trend is not None
        and a.prob_range is not None
        and (a.prob_trend - a.prob_range) > TREND_VETO_MARGIN
    )


def _option_intent(
    signal: dict[str, Any], right: str, rationale: str
) -> OrderIntent:
    """Assemble a 1-contract buy-to-open OrderIntent from a signal.

    SharpEdge trades ONE options contract. There is no equity path. The limit
    is the model premium marked up slightly so a buy is actually fillable, and
    notional() then prices off that premium (x100) instead of the underlying.
    """
    leg = build_option_leg(signal, right)
    premium = max(float(leg["est_premium"]), 0.01)
    limit = round(premium * (1 + ENTRY_LIMIT_MARKUP), 2)
    return OrderIntent(
        symbol=signal.get("symbol", "SPY"),
        side="buy",
        quantity=1,
        order_type="limit",
        limit_price=limit,
        asset="option",
        option_legs=[leg],
        rationale=rationale,
        source_signal=signal,
    )


def decide(
    signal: dict[str, Any],
    *,
    test: bool = False,
    analytics: AnalyticsContext | None = None,
) -> dict[str, Any]:
    """Turn a cockpit signal into a trade decision.

    Returns {'action': 'trade'|'stand_down', 'reason': str, 'intent': OrderIntent|None}.
    test=True forces a tiny path-validation buy regardless of edge.

    ``analytics`` (SharpEdge daily execution-state) can only veto/annotate the
    directional long, never create one. If omitted it is loaded fail-soft; stale
    analytics is ignored with a note rather than silently trusted.
    """
    spot = float(signal.get("spot") or 0)
    if spot <= 0:
        return {"action": "stand_down", "reason": "no spot in signal", "intent": None}

    if test:
        intent = _option_intent(
            signal, "call",
            "TEST MODE path validation (1 ATM call contract, limit at model premium).",
        )
        return {"action": "trade", "reason": "test mode", "intent": intent}

    regime = signal.get("gamma_regime")

    # Two regimes, two playbooks. Negative gamma = trend/breakout -> runner long.
    # Positive gamma = sticky chop -> fade the edge back to the magnet. Analytics
    # can only TIGHTEN either side (veto), never create a trade.
    if regime == "negative":
        return _runner_decision(signal, spot, analytics)
    if regime == "positive":
        return _fade_decision(signal, spot, analytics)
    return {"action": "stand_down",
            "reason": f"gamma regime '{regime}' unknown - no playbook", "intent": None}


def _runner_decision(signal, spot, analytics):
    """Negative-gamma breakout -> confirmed bullish runner = long ATM call."""
    vs_vwap = float(signal.get("vs_vwap") or 0)
    mom = float(signal.get("mom15") or 0)
    vol = float(signal.get("vol_mult") or 0)
    cw, pw = signal.get("call_wall"), signal.get("put_wall")

    if vol < MIN_VOL_MULT:
        return {"action": "stand_down",
                "reason": f"volume {vol:.1f}x < {MIN_VOL_MULT}x - move not confirmed", "intent": None}
    # sitting ON a wall = bad breakout entry
    for wall, name in ((cw, "call wall"), (pw, "put wall")):
        if wall and abs(spot - wall) / spot * 100 < WALL_PROXIMITY_PCT:
            return {"action": "stand_down",
                    "reason": f"price pinned to {name} ${wall:g}", "intent": None}
    if not (vs_vwap > MIN_VS_VWAP and mom > MIN_MOM):
        return {"action": "stand_down",
                "reason": "runner regime but no thrust (need vs-VWAP + 15m momentum)", "intent": None}

    analytics = _load_analytics(signal, analytics)
    if _range_favored(analytics):
        return {"action": "stand_down",
                "reason": (f"daily regime favors range (P_range {analytics.prob_range:.2f} > "
                           f"P_trend {analytics.prob_trend:.2f}) - runner long vetoed"),
                "intent": None}
    intent = _option_intent(
        signal, "call",
        (f"Runner day (neg gamma), price {vs_vwap:+.2f}% above VWAP, "
         f"15m mom {mom:+.2f}%, vol {vol:.1f}x confirms. Long ATM call, bias to call wall. "
         f"[analytics: {analytics.note}]"),
    )
    return {"action": "trade", "reason": "confirmed bullish runner", "intent": intent}


def _fade_decision(signal, spot, analytics):
    """Positive-gamma sticky day -> fade the edge back toward the magnet.

    At/near the call wall (resistance) we fade SHORT with a put; at/near the put
    wall (support) we fade LONG with a call. We only fade when price has actually
    reached an edge - mid-range there is nothing to fade. A fresh TREND-dominant
    daily read vetoes the fade (the edge is more likely to break than revert).
    """
    cw, pw = signal.get("call_wall"), signal.get("put_wall")
    magnet = signal.get("pin") or signal.get("max_pain")

    dist_call = (cw - spot) / spot * 100 if cw and spot <= cw else None
    dist_put = (spot - pw) / spot * 100 if pw and spot >= pw else None
    near_call = dist_call is not None and dist_call <= FADE_EDGE_PCT
    near_put = dist_put is not None and dist_put <= FADE_EDGE_PCT
    if not (near_call or near_put):
        return {"action": "stand_down",
                "reason": "sticky day but price not at an edge to fade", "intent": None}

    analytics = _load_analytics(signal, analytics)
    if _trend_favored(analytics):
        return {"action": "stand_down",
                "reason": (f"daily regime favors trend (P_trend {analytics.prob_trend:.2f} > "
                           f"P_range {analytics.prob_range:.2f}) - fade vetoed"),
                "intent": None}

    # if price hugs both edges (very tight range), fade the nearer one
    fade_call = near_call and (not near_put or (dist_call or 9) <= (dist_put or 9))
    if fade_call:
        right, edge, magnet_txt = "put", f"call wall ${cw:g}", f" toward magnet {magnet:g}" if magnet else ""
        reason = "range fade short at call wall"
    else:
        right, edge, magnet_txt = "call", f"put wall ${pw:g}", f" toward magnet {magnet:g}" if magnet else ""
        reason = "range fade long at put wall"
    intent = _option_intent(
        signal, right,
        (f"Sticky day (pos gamma), price at {edge} - fade reversion{magnet_txt}. "
         f"1 {right.upper()} contract. [analytics: {analytics.note}]"),
    )
    return {"action": "trade", "reason": reason, "intent": intent}


def load_signal(path: Path | None = None) -> dict[str, Any]:
    path = path or Path(os.path.expanduser("~/SharpEdge-System/outputs/signal.json"))
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_artifact(result: dict[str, Any], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or Path(os.path.expanduser("~/SharpEdge-System/outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"trade_intent_{stamp}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path
