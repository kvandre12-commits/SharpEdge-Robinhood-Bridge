from __future__ import annotations

import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sharpedge_robinhood_bridge.analytics_context import (
    AnalyticsContext,
    load_execution_state,
)
from sharpedge_robinhood_bridge.option_leg import (
    bs_price,
    build_option_leg,
    pick_strike,
    time_to_expiry_years,
)
from sharpedge_robinhood_bridge.trade_intent import decide, risk_check


def _runner_signal(**over):
    """A clean negative-gamma runner setup that passes gates 1-3."""
    sig = {
        "symbol": "SPY",
        "spot": 500.0,
        "gamma_regime": "negative",
        "vs_vwap": 0.10,
        "mom15": 0.10,
        "vol_mult": 2.0,
        "call_wall": 510.0,
        "put_wall": 490.0,
    }
    sig.update(over)
    return sig


def _ctx(fresh=True, prob_trend=0.6, prob_range=0.4):
    return AnalyticsContext(
        available=True, fresh=fresh, note="test ctx",
        prob_trend=prob_trend, prob_range=prob_range, final_bias="WHIP_WAIT",
    )


class DecideGateTests(unittest.TestCase):
    def test_no_spot_stands_down(self) -> None:
        self.assertEqual(decide({"spot": 0}, analytics=_ctx())["action"], "stand_down")

    def test_test_mode_forces_buy(self) -> None:
        r = decide({"symbol": "SPY", "spot": 500.0}, test=True)
        self.assertEqual(r["action"], "trade")
        self.assertEqual(r["intent"].quantity, 1)
        # SharpEdge trades options, never equity.
        self.assertEqual(r["intent"].asset, "option")

    def test_positive_gamma_midrange_stands_down(self) -> None:
        # sticky day but price is mid-range (not at an edge) -> nothing to fade
        r = decide(_runner_signal(gamma_regime="positive"), analytics=_ctx())
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("not at an edge", r["reason"])

    def test_thin_volume_stands_down(self) -> None:
        r = decide(_runner_signal(vol_mult=1.0), analytics=_ctx())
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("not confirmed", r["reason"])

    def test_wall_proximity_stands_down(self) -> None:
        # spot right on the call wall
        r = decide(_runner_signal(spot=510.0, call_wall=510.0), analytics=_ctx())
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("wall", r["reason"])


class OptionInstrumentTests(unittest.TestCase):
    """Every fired intent must be ONE option contract, never equity."""

    def test_runner_intent_is_one_option_contract(self) -> None:
        r = decide(_runner_signal(atm_iv=0.15, exp="2026-06-15"),
                   analytics=_ctx(prob_trend=0.7, prob_range=0.3))
        intent = r["intent"]
        self.assertEqual(intent.asset, "option")
        self.assertEqual(intent.quantity, 1)
        self.assertEqual(len(intent.option_legs), 1)
        self.assertEqual(intent.option_legs[0]["right"], "call")

    def test_option_limit_prices_off_premium_not_spot(self) -> None:
        # A $500 underlying option must NOT carry a ~$500 limit.
        r = decide(_runner_signal(spot=500.0, atm_iv=0.15, exp="2026-06-15"),
                   analytics=_ctx(prob_trend=0.7, prob_range=0.3))
        self.assertLess(r["intent"].limit_price, 50.0)

    def test_option_notional_within_risk_ceiling(self) -> None:
        r = decide(_runner_signal(spot=500.0, atm_iv=0.15, exp="2026-06-15"),
                   analytics=_ctx(prob_trend=0.7, prob_range=0.3))
        self.assertTrue(risk_check(r["intent"]).ok)


class OptionLegBuilderTests(unittest.TestCase):
    def test_pick_strike_atm_and_offset(self) -> None:
        self.assertEqual(pick_strike(500.4, "call", 0), 500.0)
        self.assertEqual(pick_strike(500.0, "call", 2), 502.0)
        self.assertEqual(pick_strike(500.0, "put", 2), 498.0)

    def test_bs_call_put_positive_and_intrinsic_floor(self) -> None:
        self.assertGreater(bs_price(500, 500, 1 / 365, 0.15, "call"), 0)
        # Expired ITM call collapses to intrinsic.
        self.assertEqual(bs_price(505, 500, 0.0, 0.15, "call"), 5.0)

    def test_time_to_expiry_floors_for_0dte(self) -> None:
        now = datetime(2026, 6, 15, 15, 59)  # one minute to close
        t = time_to_expiry_years({"exp": "2026-06-15"}, now=now)
        self.assertGreater(t, 0.0)

    def test_build_leg_shape(self) -> None:
        leg = build_option_leg(
            {"spot": 500.0, "atm_iv": 0.15, "exp": "2026-06-15"}, "call",
            now=datetime(2026, 6, 15, 10, 0),
        )
        self.assertEqual(leg["action"], "buy_to_open")
        self.assertEqual(leg["ratio"], 1)
        self.assertGreater(leg["est_premium"], 0)


def _sticky_signal(**over):
    """Positive-gamma sticky day with walls bracketing spot."""
    sig = {
        "symbol": "SPY", "spot": 500.0, "atm_iv": 0.15, "exp": "2026-06-15",
        "gamma_regime": "positive",
        "call_wall": 502.0, "put_wall": 490.0, "pin": 496.0,
    }
    sig.update(over)
    return sig


def _range_ctx(prob_trend=0.3, prob_range=0.7):
    return AnalyticsContext(
        available=True, fresh=True, note="range ctx",
        prob_trend=prob_trend, prob_range=prob_range, final_bias="RANGE_FADE",
    )


class DecideFadeTests(unittest.TestCase):
    """Positive-gamma fade-the-edge playbook (the 263 RANGE_FADE days)."""

    def test_fade_short_put_at_call_wall(self) -> None:
        # spot just below the call wall -> fade SHORT with a put
        r = decide(_sticky_signal(spot=501.0, call_wall=502.0), analytics=_range_ctx())
        self.assertEqual(r["action"], "trade")
        self.assertEqual(r["intent"].option_legs[0]["right"], "put")
        self.assertIn("call wall", r["reason"])

    def test_fade_long_call_at_put_wall(self) -> None:
        # spot just above the put wall -> fade LONG with a call
        r = decide(_sticky_signal(spot=490.5, put_wall=490.0, call_wall=505.0),
                   analytics=_range_ctx())
        self.assertEqual(r["action"], "trade")
        self.assertEqual(r["intent"].option_legs[0]["right"], "call")
        self.assertIn("put wall", r["reason"])

    def test_fade_midrange_stands_down(self) -> None:
        r = decide(_sticky_signal(spot=496.0), analytics=_range_ctx())
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("not at an edge", r["reason"])

    def test_fade_vetoed_when_daily_favors_trend(self) -> None:
        # at the edge, but fresh daily regime says TREND -> fade vetoed
        r = decide(_sticky_signal(spot=501.0, call_wall=502.0),
                   analytics=AnalyticsContext(available=True, fresh=True, note="trend",
                                              prob_trend=0.75, prob_range=0.25))
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("favors trend", r["reason"])

    def test_fade_one_option_contract(self) -> None:
        r = decide(_sticky_signal(spot=501.0, call_wall=502.0), analytics=_range_ctx())
        self.assertEqual(r["intent"].asset, "option")
        self.assertEqual(r["intent"].quantity, 1)

    def test_fade_high_conviction_when_coiled(self) -> None:
        # tight channel (coil) + expected move that reaches the magnet -> HIGH
        sig = _sticky_signal(spot=501.0, call_wall=502.0, pin=496.0,
                             micro={"ch_width_pct": 0.10},
                             magnitude={"exp_move_realized_pct": 2.0})
        r = decide(sig, analytics=_range_ctx())
        self.assertEqual(r["action"], "trade")
        self.assertIn("HIGH", r["reason"])
        self.assertIn("coiled", r["intent"].rationale)

    def test_fade_no_room_stands_down(self) -> None:
        # at the edge AND sitting on the magnet (wall~=magnet~=spot) -> no room
        r = decide(_sticky_signal(spot=496.0, call_wall=496.3, pin=496.0, put_wall=490.0),
                   analytics=_range_ctx())
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("nothing to fade", r["reason"])


class DecideAnalyticsGateTests(unittest.TestCase):
    def test_runner_fires_when_trend_analytics_confirms(self) -> None:
        r = decide(_runner_signal(), analytics=_ctx(prob_trend=0.7, prob_range=0.3))
        self.assertEqual(r["action"], "trade")
        self.assertIn("test ctx", r["intent"].rationale)

    def test_runner_vetoed_when_fresh_range_analytics_dominates(self) -> None:
        r = decide(_runner_signal(), analytics=_ctx(prob_trend=0.3, prob_range=0.7))
        self.assertEqual(r["action"], "stand_down")
        self.assertIn("favors range", r["reason"])

    def test_stale_range_analytics_does_not_veto(self) -> None:
        # Same dominant-range numbers but STALE -> ignored, trade still fires.
        r = decide(_runner_signal(), analytics=_ctx(fresh=False, prob_trend=0.3, prob_range=0.7))
        self.assertEqual(r["action"], "trade")

    def test_unavailable_analytics_does_not_block(self) -> None:
        ctx = AnalyticsContext(available=False, fresh=False, note="missing")
        r = decide(_runner_signal(), analytics=ctx)
        self.assertEqual(r["action"], "trade")


class AnalyticsLoaderTests(unittest.TestCase):
    HEADER = "session_date,symbol,prob_trend_fused,prob_range_fused,dealer_state_hint,execution_score,final_bias\n"

    def _write(self, tmp: Path, rows: str) -> Path:
        p = tmp / "execution_state_daily.csv"
        p.write_text(self.HEADER + rows, encoding="utf-8")
        return p

    def test_missing_file_unavailable(self) -> None:
        ctx = load_execution_state(Path("/no/such/file.csv"))
        self.assertFalse(ctx.available)
        self.assertFalse(ctx.fresh)

    def test_wrong_symbol_unavailable(self) -> None:
        with TemporaryDirectory() as d:
            p = self._write(Path(d), "2026-06-10,WMT,0.6,0.4,NEUTRAL,20,WHIP_WAIT\n")
            ctx = load_execution_state(p, symbol="SPY")
        self.assertFalse(ctx.available)

    def test_fresh_row_parsed(self) -> None:
        with TemporaryDirectory() as d:
            p = self._write(Path(d), "2026-06-10,SPY,0.62,0.38,NEUTRAL,24,WHIP_WAIT\n")
            ctx = load_execution_state(p, symbol="SPY", today=date(2026, 6, 12), max_age_days=5)
        self.assertTrue(ctx.available)
        self.assertTrue(ctx.fresh)
        self.assertEqual(ctx.age_days, 2)
        self.assertAlmostEqual(ctx.prob_trend, 0.62)

    def test_stale_row_not_fresh(self) -> None:
        with TemporaryDirectory() as d:
            p = self._write(Path(d), "2026-05-20,SPY,0.5,0.5,NEUTRAL,10,WHIP_WAIT\n")
            ctx = load_execution_state(p, symbol="SPY", today=date(2026, 6, 12), max_age_days=5)
        self.assertTrue(ctx.available)
        self.assertFalse(ctx.fresh)
        self.assertIn("STALE", ctx.note)


if __name__ == "__main__":
    unittest.main()
