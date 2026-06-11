# Architecture

## Repo role

This repo is the command-routing layer between:

- SharpEdge strategy/research systems
- broker-facing Robinhood command intents
- approval-gated execution handoff paths

## Boundaries

### Keep out of this repo

- portfolio research pipelines
- market-data ingestion
- agent runtime / model orchestration
- raw OAuth token plumbing

### Put in this repo

- command catalogs
- alias normalization
- support-tier decisions
- approval policy rules
- future custom handlers for unsupported-but-buildable commands

## Initial design

1. `catalog.py`
   - command registry
   - alias mapping
   - support tiers
2. `router.py`
   - convert a command request into an execution plan
3. `cli.py`
   - local inspection / testing
4. `tests/`
   - prevent policy drift

## Design principle

Do not pretend unsupported commands are verified.

Instead, classify them honestly as either:

- verified
- delegate-only
- custom-logic candidate
- unknown

That gives us room to build new logic without lying about source validation.
