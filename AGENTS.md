# AGENTS.md

## Repo purpose

This repo owns **Robinhood app-command logic** for SharpEdge.

It should answer questions like:

- what command was requested
- whether the command is verified, delegate-only, or custom logic we need to build
- what route the command should take
- what approval policy applies

## What belongs here

- command catalogs
- alias normalization
- policy/routing rules
- approval-gated execution planning
- custom handlers for unsupported-but-buildable commands
- tests that prevent support-tier drift

## What does NOT belong here

- full trading strategy pipelines
- market-data ingestion
- agent runtime / model orchestration
- raw OAuth credential plumbing
- fake claims that a command is source-verified when it is not

## Safety rules

1. Do not label a command as verified unless it is actually verified.
2. Active trading commands must stay approval-gated by default.
3. Unknown commands must remain unknown until explicitly modeled.
4. Custom-logic candidates are allowed, but they must not masquerade as public MCP support.
5. Prefer simple routing logic over clever nonsense.

## Command buckets

- `research_read`
- `active_trading_preview`
- `active_trading_write`
- `custom_logic_candidate`
- `unknown`

## Route buckets

- `public_mcp_read`
- `chatgpt_delegate`
- `custom_logic_local`
- `custom_logic_required`
- `unknown`

## Development rules

- Keep modules small and cohesive.
- Prefer updating the command catalog over scattering one-off conditionals.
- Add tests whenever support tier or routing behavior changes.
- If a command gains real implementation, update docs and tests in the same change.

## First implementation targets

Implemented:

- `create_watchlist`

Next strong candidates:

- `get_watchlists`
- `update_watchlist`

Those are strong watchlist-state commands for bridge-side logic in this repo.
