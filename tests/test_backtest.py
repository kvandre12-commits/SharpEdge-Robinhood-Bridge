from __future__ import annotations

import unittest

from sharpedge_robinhood_bridge.analytics_context import AnalyticsContext
from sharpedge_robinhood_bridge.backtest import (
    grade_signal,
    run_backtest,
)


def _runner(**over):
    sig = {
        "session": "2026-06-10",
        "symbol": "SPY",
        "spot": 500.0,
        "atm_iv": 0.15,
        "exp": "2026-06-10",
        "gamma_regime": "negative",
        "vs_vwap": 0.10,
        "mom15": 0.10,
        "vol_mult": 2.0,
        "call_wall": 510.0,
        "put_wall": 490.0,
    }
    sig.update(over)
    return sig


def _ctx(fresh=True, prob_trend=0.7, prob_range=0.3):
    return AnalyticsContext(
        available=True, fresh=fresh, note="ctx",
        prob_trend=prob_trend, prob_range=prob_range, final_bias="WHIP_WAIT",
    )


class GradeSignalTests(unittest.TestCase):
    def test_winning_long_call_is_win(self) -> None:
        g = grade_signal(_runner(), 0.40, analytics=_ctx())
        self.assertEqual(g.action, "trade")
        self.assertEqual(g.direction, "call")
        self.assertAlmostEqual(g.signed_return_pct, 0.40)
        self.assertTrue(g.win)

    def test_losing_long_call_is_loss(self) -> None:
        g = grade_signal(_runner(), -0.30, analytics=_ctx())
        self.assertAlmostEqual(g.signed_return_pct, -0.30)
        self.assertFalse(g.win)

    def test_stand_down_has_no_direction(self) -> None:
        g = grade_signal(_runner(gamma_regime="positive"), 0.50, analytics=_ctx())
        self.assertEqual(g.action, "stand_down")
        self.assertIsNone(g.direction)
        self.assertIsNone(g.win)

    def test_analytics_veto_makes_it_stand_down(self) -> None:
        g = grade_signal(_runner(), 0.50, analytics=_ctx(prob_trend=0.3, prob_range=0.7))
        self.assertEqual(g.action, "stand_down")
        self.assertIn("favors range", g.reason)


class RunBacktestTests(unittest.TestCase):
    def test_aggregates_win_rate_and_edge(self) -> None:
        records = [
            (_runner(session="d1"), 0.40),   # win  +0.40
            (_runner(session="d2"), 0.20),   # win  +0.20
            (_runner(session="d3"), -0.30),  # loss -0.30
        ]
        res = run_backtest(records)
        self.assertEqual(res.n_signals, 3)
        self.assertEqual(res.n_trades, 3)
        self.assertEqual(res.n_wins, 2)
        self.assertAlmostEqual(res.win_rate, 2 / 3)
        self.assertAlmostEqual(res.avg_signed_return, (0.40 + 0.20 - 0.30) / 3)

    def test_stand_downs_excluded_from_trade_stats(self) -> None:
        records = [
            (_runner(session="d1"), 0.40),                       # trade
            (_runner(session="d2", gamma_regime="positive"), 9.0),  # stand down
        ]
        res = run_backtest(records)
        self.assertEqual(res.n_signals, 2)
        self.assertEqual(res.n_trades, 1)
        # the stand-down reason is still bucketed for state analysis
        self.assertIn("positive gamma / sticky chop - no directional edge",
                      [r for r in res.by_reason])

    def test_point_in_time_analytics_veto_applied(self) -> None:
        recs = [(_runner(session="d1"), 0.50)]
        ctxmap = {"d1": _ctx(prob_trend=0.3, prob_range=0.7)}
        res = run_backtest(recs, analytics_for=ctxmap)
        self.assertEqual(res.n_trades, 0)  # vetoed point-in-time

    def test_summary_shape(self) -> None:
        res = run_backtest([(_runner(session="d1"), 0.40)])
        s = res.summary()
        self.assertEqual(s["n_trades"], 1)
        self.assertIn("by_reason", s)


if __name__ == "__main__":
    unittest.main()
