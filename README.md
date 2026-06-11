# SharpEdge Robinhood Bridge

Focused Robinhood app-command logic for SharpEdge.

This repo exists to keep broker-facing command logic out of the wrong places.
It separates:

- capability registry
- command alias normalization
- approval-gated execution routing
- custom-logic candidates that are not yet source-verified

## Why a separate repo

`SharpEdge-System` should stay focused on trading-system artifacts and workflows.
`code_puppy` should stay focused on agent runtime, plugins, and OAuth plumbing.

This repo is the middle layer:

- **What command did the app ask for?**
- **Is it read-only research, active trading, or custom logic we still need to build?**
- **Should it route to public MCP read logic, approval-gated delegation, or a future custom handler?**

## Current command buckets

- `research_read`
- `active_trading_preview`
- `active_trading_write`
- `custom_logic_candidate`
- `unknown`

## Current route buckets

- `public_mcp_read`
- `chatgpt_delegate`
- `custom_logic_required`
- `unknown`

## Example commands

Verified public research reads:

- `get_portfolio`
- `get_positions`
- `get_watchlist`
- `get_quote`

Approval-gated trading intents:

- `order_draft`
- `order_submit`
- `order_cancel`
- `order_replace`

Custom-logic candidates we can build here:

- `create_watchlist`
- `update_watchlist`
- `get_watchlists`
- `get_option_watchlist`
- `get_option_chains`
- `get_option_instruments`

## Repo guidance

- `AGENTS.md`
- `docs/architecture.md`
- `docs/command_policy.md`
- `docs/governance_model.md`
- `docs/roadmap.md`

Those files define what belongs here, what does not, and how command support should be classified without lying to ourselves.

## CLI

Classify a command:

```bash
python -m sharpedge_robinhood_bridge classify create_watchlist
```

Build a command plan:

```bash
python -m sharpedge_robinhood_bridge plan order_submit --payload '{"symbol":"SPY"}'
```

## Dev test

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
