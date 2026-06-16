"""Option-leg builder: turn a SharpEdge signal into one tradeable contract.

SharpEdge trades **one options contract**, never equity. This module owns the
"which contract" decision: right (call/put), strike, expiry, and a *premium*
estimate used for the limit price and notional math.

Pricing is a lightweight Black-Scholes (r=0, q=0). It is an ESTIMATE for sizing
a limit order, not a mark. For 0DTE the time-to-expiry is floored so the model
never collapses to pure intrinsic and hand back a $0 premium.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

# SPY lists $1 strikes. Centralize so a different underlying is a one-line change.
STRIKE_INCREMENT = 1.0
# 0DTE never prices off T=0 (would be intrinsic-only). Floor the clock.
MIN_HOURS_TO_EXPIRY = 0.5
TRADING_CLOSE_HOUR = 16  # local-time approximation of the cash close
YEAR_HOURS = 24 * 365


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, t_years: float, iv: float, right: str) -> float:
    """Black-Scholes call/put price with r=q=0. Returns a non-negative premium."""
    right = right.lower()
    if t_years <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        intrinsic = (spot - strike) if right == "call" else (strike - spot)
        return round(max(intrinsic, 0.0), 2)
    vol_t = iv * math.sqrt(t_years)
    d1 = (math.log(spot / strike) + 0.5 * iv * iv * t_years) / vol_t
    d2 = d1 - vol_t
    if right == "call":
        price = spot * _norm_cdf(d1) - strike * _norm_cdf(d2)
    else:
        price = strike * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
    return round(max(price, 0.0), 2)


def time_to_expiry_years(signal: dict[str, Any], now: datetime | None = None) -> float:
    """Years to expiry from ``signal['exp']`` (YYYY-MM-DD), floored for 0DTE."""
    exp_raw = signal.get("exp")
    if not exp_raw:
        return MIN_HOURS_TO_EXPIRY / YEAR_HOURS
    now = now or datetime.now()
    try:
        exp = datetime.strptime(str(exp_raw), "%Y-%m-%d").date()
    except ValueError:
        return MIN_HOURS_TO_EXPIRY / YEAR_HOURS
    days = (exp - now.date()).days
    if days < 0:
        return 0.0  # expired
    if days == 0:
        close = now.replace(hour=TRADING_CLOSE_HOUR, minute=0, second=0, microsecond=0)
        hours = max((close - now).total_seconds() / 3600.0, MIN_HOURS_TO_EXPIRY)
        return hours / YEAR_HOURS
    return days / 365.0


def pick_strike(spot: float, right: str, offset_steps: int = 0) -> float:
    """Nearest standard strike, shifted ``offset_steps`` increments OTM."""
    atm = round(spot / STRIKE_INCREMENT) * STRIKE_INCREMENT
    direction = 1 if right.lower() == "call" else -1
    return round(atm + direction * offset_steps * STRIKE_INCREMENT, 2)


def build_option_leg(
    signal: dict[str, Any],
    right: str,
    *,
    now: datetime | None = None,
    strike_offset: int = 0,
) -> dict[str, Any]:
    """signal + right -> a single buy-to-open leg with an estimated premium."""
    spot = float(signal.get("spot") or 0)
    iv = float(signal.get("atm_iv") or 0)
    strike = pick_strike(spot, right, strike_offset)
    t = time_to_expiry_years(signal, now)
    premium = bs_price(spot, strike, t, iv, right)
    return {
        "right": right.lower(),
        "strike": strike,
        "expiry": signal.get("exp"),
        "action": "buy_to_open",
        "ratio": 1,
        "est_premium": premium,
        "iv": round(iv, 4),
    }
