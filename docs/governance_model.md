# Governance Model

## Purpose

This document maps the SharpEdge Robinhood governance model across repos,
routing layers, approval gates, and trust boundaries.

The core idea is simple:

- research may be automated more freely than trading
- command classification must be honest
- live-order authority stays behind explicit operator approval
- unsupported commands may be built, but they must not masquerade as verified public support

## Governance layers

### 1. Operator layer
The human operator is the final authority.

Operator powers:

- decide whether a trade is allowed
- approve or reject live-order actions
- decide whether a custom command should be implemented
- choose which repo owns which responsibility

This layer overrides every lower automation layer.

### 2. Command governance layer
Repo:

- `SharpEdge-Robinhood-Bridge`

This repo decides:

- what a requested command means
- whether it is verified, delegate-only, custom logic, or unknown
- which route it should take
- what approval policy applies

This is the policy brain for Robinhood app-command handling.

### 3. Strategy and artifact layer
Repo:

- `SharpEdge-System`

This repo produces:

- market/state/research artifacts
- operator briefs
- Robinhood monitor artifacts
- beta execution handoffs

It may recommend or prepare. It does not grant autonomous live trading authority.

### 4. Agent runtime and OAuth plumbing layer
Repo:

- `code_puppy`

This repo owns:

- agent runtime
- plugin hooks
- MCP OAuth support
- ChatGPT Robinhood delegation artifact generation

It is an orchestration layer, not the trading-governance authority.

### 5. Connector / broker layer
External systems:

- hosted Robinhood MCP bridge
- ChatGPT Robinhood connector
- Robinhood itself

These systems may expose real broker-side capabilities, but local code must not assume a capability exists unless it has been verified or explicitly modeled.

## Repo boundaries

### `SharpEdge-Robinhood-Bridge`
Owns:

- command catalog
- alias normalization
- routing policy
- approval policy
- custom-logic implementation candidates

Does not own:

- market data ingestion
- portfolio analytics pipeline
- raw OAuth token management
- general-purpose AI runtime

### `SharpEdge-System`
Owns:

- strategy outputs
- deterministic trading artifacts
- monitor and beta-execution summaries

Does not own:

- broker command vocabulary governance
- low-level agent runtime concerns

### `code_puppy`
Owns:

- agent execution framework
- plugin/tool system
- MCP auth plumbing
- ChatGPT delegation handoff tooling

Does not own:

- final command support policy for SharpEdge Robinhood bridge work
- autonomous live trade authorization

## Authority ladder

### Tier A — verified research reads
Examples:

- `get_portfolio`
- `get_positions`
- `get_watchlist`
- `get_quote`

Category:

- `research_read`

Route:

- `public_mcp_read`

Approval posture:

- no special trade approval required
- still subject to normal operator oversight

### Tier B — approval-gated previews
Examples:

- `create_order_draft`
- `order_draft`

Category:

- `active_trading_preview`

Route:

- `chatgpt_delegate`

Approval posture:

- `operator_confirm_required`

### Tier C — approval-gated live-order intents
Examples:

- `order_submit`
- `order_cancel`
- `order_replace`

Category:

- `active_trading_write`

Route:

- `chatgpt_delegate`

Approval posture:

- `operator_confirm_required`
- no silent autonomous submit/replace/cancel

### Tier D — custom-logic candidates
Examples:

- `create_watchlist`
- `get_watchlists`
- `update_watchlist`
- `get_option_chains`
- `get_option_instruments`

Category:

- `custom_logic_candidate`

Route:

- `custom_logic_required`

Approval posture:

- implementation required before claiming support
- must not be labeled verified public support until that is true

### Tier E — unknown commands
Category:

- `unknown`

Route:

- `unknown`

Approval posture:

- blocked from trust escalation until modeled

## Source-of-truth hierarchy

When deciding what a command is allowed to mean, use this order:

1. explicit repo policy and tests in `SharpEdge-Robinhood-Bridge`
2. verified public source inventories
3. authenticated live bridge validation when available
4. custom handler logic built in this repo
5. human operator decision

Important:

- conversational guesses are not source of truth
- plausible naming is not source of truth
- old assumptions must lose to updated verification

## Trust boundaries

### Boundary 1 — research vs trading
A read command is not a trade command.

Do not let:

- quote monitoring
- position lookup
- watchlist reading

turn into implied order authority.

### Boundary 2 — local code vs hosted connector
Local code may generate handoffs or plans.
It does not automatically inherit direct broker execution rights from the ChatGPT connector.

### Boundary 3 — verified support vs buildable support
Some commands are buildable even if they are not currently source-verified.
That is fine.

What is not fine:

- calling them verified when they are not
- routing them as if public support already exists

### Boundary 4 — planning vs execution
SharpEdge may:

- classify
- recommend
- prepare
- draft

But execution authority for live trading remains explicitly gated.

## OAuth/control-plane note
The user keeps both:

- GitHub OAuth
- Robinhood OAuth

on the ChatGPT apps/oauth page.

That means connector-side access may exist outside local repo code.
Local logic must still preserve the governance model above and not assume blanket execution authority.

## Change management rules

When governance changes:

1. update the command catalog
2. update tests
3. update policy docs
4. update governance docs if authority boundaries moved

Examples of governance-changing events:

- a command moves from custom candidate to real handler
- a command becomes live-bridge verified
- an approval rule changes
- a new execution route is introduced

## Current operating principle

The model is intentionally conservative:

- honest reads
- approval-gated writes
- explicit custom-build lane
- no pretending

That is the governance model.
