from __future__ import annotations

import unittest

from sharpedge_robinhood_bridge import plan_command


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

    def test_custom_logic_candidate_is_not_labeled_verified(self) -> None:
        plan = plan_command("create_watchlist")
        self.assertTrue(plan.matched)
        self.assertEqual(plan.category, "custom_logic_candidate")
        self.assertEqual(plan.support_tier, "custom_logic_candidate")
        self.assertEqual(plan.route, "custom_logic_required")

    def test_unknown_command_stays_unknown(self) -> None:
        plan = plan_command("launch_missiles")
        self.assertFalse(plan.matched)
        self.assertEqual(plan.route, "unknown")


if __name__ == "__main__":
    unittest.main()
