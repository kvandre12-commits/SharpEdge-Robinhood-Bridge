# App-Ready v0.1.0 Command Spec

This document is the product-facing command-language source for early app conversion work.

Use it when ChatGPT, Codex, or any downstream app-construction workflow needs stable command intent, purpose wording, and governance-safe descriptions.

## Scope

Current implemented custom workflow-state commands:

- `create_watchlist`
- `get_watchlists`

These commands operate on **local SharpEdge workflow-state watchlists**.
They do **not** claim verified public Robinhood watchlist write/read directory support.

## Core model

Watchlists are **workflow states**, not passive storage bins.

Canonical workflow progression:

```text
Research -> Candidate -> High Conviction -> Execution Queue -> Order Review -> Order Placement
```

## Command: `create_watchlist`

### Purpose
Create a new custom watchlist for organizing trading ideas by workflow stage.

### Use when
A new workflow, strategy, or research bucket is needed.

### Behavior

- creates a local SharpEdge workflow-state queue
- enforces canonical workflow-state names
- prevents duplicate queues for the same workflow state
- may include initial symbols and an optional note

### Inputs

- `name` or `workflow_state`
- optional `symbols`
- optional `note`

### Returns

- created watchlist state queue
- existing watchlist if the state queue already exists
- validation error for unknown workflow-state names

### Governance note
This is local SharpEdge bridge logic, not claimed Robinhood watchlist-write support.

## Command: `get_watchlists`

### Purpose
Retrieve all watchlists available to the user.

### Use when
The agent needs to discover which workflow, strategy, or research watchlists currently exist.

### Behavior

- returns all local SharpEdge workflow-state watchlists
- sorts them in canonical workflow-stage order
- includes schema version and storage path metadata

### Inputs

- none required

### Returns

- watchlist collection
- canonical stage ordering
- total watchlist count

### Governance note
This is local SharpEdge bridge logic, not claimed Robinhood watchlist-directory support.

## Product wording rule

For v0.1.0 app conversion:

- prefer precise command contracts over vague marketing copy
- prefer workflow-state language over generic list-storage language
- never imply broker authority that does not exist
- never imply verified public support where only local custom logic exists
