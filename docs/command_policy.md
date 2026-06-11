# Command Policy

## Purpose

This repo separates Robinhood app commands into honest execution lanes.

We care about three questions:

1. Is the command verified?
2. Is it read-only or trading-sensitive?
3. Should it route to public MCP read logic, delegated approval flow, or new custom logic?

## Categories

### `research_read`
Use for read-only commands with verified public support.

Examples:

- `get_portfolio`
- `get_positions`
- `get_watchlist`
- `get_quote`

Expected route:

- `public_mcp_read`

### `active_trading_preview`
Use for order-preview or draft-style commands.

Examples:

- `create_order_draft`
- `order_draft`

Expected route:

- `chatgpt_delegate`

Approval policy:

- `operator_confirm_required`

### `active_trading_write`
Use for commands that can place, replace, or cancel live orders.

Examples:

- `order_submit`
- `order_cancel`
- `order_replace`

Expected route:

- `chatgpt_delegate`

Approval policy:

- `operator_confirm_required`

### `custom_logic_candidate`
Use for commands that are not currently verified in the public source but are reasonable to implement as bridge-side logic.

Examples:

- `create_watchlist`
- `get_watchlists`
- `update_watchlist`
- `get_option_chains`
- `get_option_instruments`

Expected route:

- `custom_logic_required`

### `unknown`
Use when we do not have a modeled command yet.

Expected route:

- `unknown`

## Policy constraints

- Do not silently upgrade unknown/custom commands to verified.
- Do not silently downgrade trading-sensitive commands into harmless reads.
- Do not remove approval gating from live-order style commands unless the repo policy changes explicitly.
- Prefer one catalog entry plus tests over ad-hoc routing branches.

## Implementation standard

When adding a new command:

1. add or update the command spec
2. define category, support tier, route, and approval policy
3. add tests
4. update docs if behavior meaningfully changed
