# Roadmap

## Near-term

### 1. Watchlist command slice
Current state:

- `create_watchlist` implemented as local custom logic

Next commands:

- `get_watchlists`
- `update_watchlist`

Goal:

- extend the watchlist workflow slice beyond creation
- keep policy boundaries intact

### 2. Handler interface
Add a clean handler abstraction so catalog entries can point to actual implementations without bloating the router.

### 3. Output contracts
Define stable response schemas for:

- success
- blocked / approval-required
- unsupported
- unknown

## Mid-term

### 4. Option command candidates
Evaluate and potentially implement:

- `get_option_chains`
- `get_option_instruments`
- `get_option_watchlist`
- `get_equity_tradability`

### 5. Live bridge verification layer
Add an optional authenticated capability check path so the repo can compare:

- public-source assumptions
- local custom logic
- live hosted bridge inventory

## Long-term

### 6. Bridge integration adapters
Add adapters for:

- public MCP read paths
- delegate handoff generation
- custom logic execution backends

### 7. Policy audit tooling
Add tooling that reports:

- commands by category
- commands by route
- commands missing tests or docs
