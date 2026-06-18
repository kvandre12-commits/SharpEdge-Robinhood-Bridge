# SharpEdge-Robinhood-Bridge Ownership

## What this repo is

SharpEdge-Robinhood-Bridge owns Robinhood app-command classification, routing,
and approval-gated execution planning for SharpEdge.

It is a broker-facing command-policy layer, not a trading brain.

## Owns

- Robinhood command catalog.
- Command alias normalization.
- Capability/support-tier classification.
- Approval-gated execution routing.
- Local custom command handlers where explicitly implemented.
- Tests that prevent command-support drift.

## Does not own

- Market data ingestion.
- Signal generation.
- Trade Gate analytics.
- Android UI rendering.
- Phone Companion orchestration.
- Code Puppy core runtime.
- Autonomous live order submission.
- Raw OAuth credential plumbing.

## Stable source areas

```text
src/
tests/
docs/
README.md
AGENTS.md
OWNERSHIP.md
pyproject.toml
```

## Generated/runtime artifact areas

```text
outputs/
```

Treat `outputs/` as runtime evidence unless a task explicitly asks to update a
fixture/example.

## Safety boundary

Active trading commands must remain approval-gated.

Unknown or unverified commands must not be described as supported. Custom logic
is allowed only when explicitly modeled and tested.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

## Agent entrypoints

Read first:

1. `OWNERSHIP.md`
2. `AGENTS.md`
3. `README.md`
4. `docs/command_policy.md`
5. `docs/governance_model.md`

Then work only on broker command routing/policy unless the task explicitly says
otherwise.
