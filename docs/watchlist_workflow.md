# Watchlist Workflow

## Core principle

**Purpose:** Create a new custom watchlist for organizing trading ideas by workflow stage.

**Use when:** A new workflow, strategy, or research bucket is needed.

Related command purpose for `get_watchlists`: retrieve all watchlists available to the user within SharpEdge's local workflow layer, in canonical stage order.

Related command use when for `get_watchlists`: the agent needs to discover which workflow, strategy, or research watchlists currently exist.

In SharpEdge, watchlists are **workflow states**, not passive storage bins.

A symbol does not merely sit in a list. It moves through a governed decision
pipeline, and each state implies:

- what the symbol currently means
- what actions are allowed
- what evidence is required to move forward
- what commands make sense at that stage

## State progression

```text
Research -> Candidate -> High Conviction -> Execution Queue -> Order Review -> Order Placement
```

## State definitions

### 1. Research
The symbol is being explored.

Allowed posture:

- read-only data gathering
- thesis formation
- no order authority implied

Typical commands:

- `get_quote`
- `get_fundamentals`
- `get_historicals`
- `get_news`
- `get_earnings`
- `get_ratings`
- `search`

### 2. Candidate
The symbol has passed initial screening and is worth tracking.

Allowed posture:

- continued read/monitor work
- workflow admission into tracked symbol sets
- still no order authority implied

Typical watchlist commands:

- `create_watchlist` (implemented local custom logic)
- `get_watchlists` (implemented local custom logic)
- `get_watchlist`
- `update_watchlist`

Typical research commands:

- `get_positions`
- `get_order_history`
- `get_quote`

### 3. High Conviction
The symbol has a strong thesis, setup alignment, or elevated readiness.

Allowed posture:

- active monitoring
- setup review
- execution planning can begin
- still not equivalent to order placement

Typical commands:

- `get_watchlist`
- `get_positions`
- `get_quote`
- `get_option_chains`
- `get_option_instruments`
- `get_equity_tradability`

Governance note:

- some of these are currently custom-logic candidates, not verified public support

### 4. Execution Queue
A symbol is awaiting formal trade-setup handling.

Allowed posture:

- draft preparation
- queueing for review
- explicit operator review path

Typical commands:

- `create_order_draft`
- `order_draft`
- `get_watchlist`
- `update_watchlist`

### 5. Order Review
A draft exists and must be reviewed before live action.

Allowed posture:

- inspect draft
- confirm risk
- confirm price limits
- confirm operator intent

Typical commands:

- `order_draft`
- `get_positions`
- `get_order_history`
- `update_watchlist`

Governance note:

- this is still approval-gated
- review is not execution

### 6. Order Placement
A live-order style action is being requested.

Allowed posture:

- explicit operator-confirmed order action only
- no silent execution

Typical commands:

- `order_submit`
- `order_replace`
- `order_cancel`

Governance note:

- all live-order style commands remain `operator_confirm_required`

## Command family mapping

### Research-family commands
Belong mainly in:

- Research
- Candidate
- High Conviction

Examples:

- `get_quote`
- `get_fundamentals`
- `get_historicals`
- `get_news`
- `get_earnings`
- `get_ratings`

### Watchlist-state commands
Belong mainly in:

- Candidate
- High Conviction
- Execution Queue
- Order Review

Examples:

- `create_watchlist` (implemented local custom logic)
- `get_watchlists` (implemented local custom logic)
- `get_watchlist`
- `update_watchlist`

### Trading-preview commands
Belong mainly in:

- Execution Queue
- Order Review

Examples:

- `create_order_draft`
- `order_draft`

### Live-order commands
Belong only in:

- Order Placement

Examples:

- `order_submit`
- `order_replace`
- `order_cancel`

## Governance implications

1. A watchlist entry should represent **state**, not just membership.
2. A symbol moving states should eventually be driven by explicit transition rules.
3. Research membership must not imply trading authority.
4. Execution Queue and Order Review are distinct; drafting is not placement.
5. Order Placement always remains approval-gated.

## SharpEdge policy statement

Use this interpretation across the bridge work:

> Watchlists are workflow states, not storage bins. Symbols move from Research to Candidate to High Conviction to Execution Queue to Order Review to Order Placement, and each state determines the permitted commands, evidence requirements, and approval posture.
