from __future__ import annotations

import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from sharpedge_robinhood_bridge import plan_command, run_command


class RouterTests(unittest.TestCase):
    def test_verified_read_alias_maps_to_public_route(self) -> None:
        plan = plan_command("get_portfolio")
        self.assertTrue(plan.matched)
        self.assertEqual(plan.actual_command_name, "robinhood_get_portfolio")
        self.assertEqual(plan.category, "research_read")
        self.assertEqual(plan.route, "public_mcp_read")

    def test_delegate_write_requires_operator_confirmation(self) -> None:
        plan = plan_command("order_submit", {"symbol": "SPY"})
        self.assertTrue(plan.matched)
        self.assertEqual(plan.category, "active_trading_write")
        self.assertEqual(plan.route, "chatgpt_delegate")
        self.assertEqual(plan.approval_policy, "operator_confirm_required")
        self.assertEqual(plan.payload["symbol"], "SPY")

    def test_create_watchlist_is_local_custom_logic(self) -> None:
        plan = plan_command("create_watchlist")
        self.assertTrue(plan.matched)
        self.assertEqual(plan.category, "custom_logic_candidate")
        self.assertEqual(plan.support_tier, "implemented_custom_logic")
        self.assertEqual(plan.route, "custom_logic_local")
        self.assertEqual(plan.handler_name, "create_watchlist")

    def test_get_watchlists_is_local_custom_logic(self) -> None:
        plan = plan_command("get_watchlists")
        self.assertTrue(plan.matched)
        self.assertEqual(plan.category, "custom_logic_candidate")
        self.assertEqual(plan.support_tier, "implemented_custom_logic")
        self.assertEqual(plan.route, "custom_logic_local")
        self.assertEqual(plan.handler_name, "get_watchlists")

    def test_run_create_watchlist_persists_workflow_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = run_command(
                "create_watchlist",
                {"name": "Candidate", "symbols": ["aapl", "msft", "AAPL"]},
                base_dir=Path(temp_dir),
            )
            self.assertTrue(result.executed)
            self.assertEqual(result.status, "created")
            watchlist = result.result["watchlist"]
            self.assertEqual(watchlist["workflow_state"], "Candidate")
            self.assertEqual(watchlist["symbols"], ["AAPL", "MSFT"])

    def test_run_create_watchlist_returns_existing_state_queue(self) -> None:
        with TemporaryDirectory() as temp_dir:
            first = run_command("create_watchlist", {"name": "Candidate"}, base_dir=Path(temp_dir))
            second = run_command("create_watchlist", {"name": "candidate"}, base_dir=Path(temp_dir))
            self.assertEqual(first.status, "created")
            self.assertEqual(second.status, "exists")

    def test_run_get_watchlists_returns_canonical_order(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            run_command("create_watchlist", {"name": "Order Review"}, base_dir=base_dir)
            run_command("create_watchlist", {"name": "Candidate"}, base_dir=base_dir)
            run_command("create_watchlist", {"name": "Research"}, base_dir=base_dir)

            result = run_command("get_watchlists", {}, base_dir=base_dir)
            self.assertTrue(result.executed)
            self.assertEqual(result.status, "ok")
            self.assertEqual(result.result["total_watchlists"], 3)
            names = [item["workflow_state"] for item in result.result["watchlists"]]
            self.assertEqual(names, ["Research", "Candidate", "Order Review"])

    def test_invalid_watchlist_state_returns_validation_result(self) -> None:
        result = run_command("create_watchlist", {"name": "Moon Mission"})
        self.assertFalse(result.executed)
        self.assertEqual(result.status, "invalid_payload")
        self.assertIn("allowed states", result.summary)

    def test_unknown_command_stays_unknown(self) -> None:
        plan = plan_command("launch_missiles")
        self.assertFalse(plan.matched)
        self.assertEqual(plan.route, "unknown")
        self.assertEqual(plan.handler_name, "")


if __name__ == "__main__":
    unittest.main()
