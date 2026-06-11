from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .workflow_states import normalize_workflow_state, workflow_state_labels

STORE_DIR = "outputs"
STORE_NAME = "watchlists.json"
SCHEMA_VERSION = "watchlists.v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _store_path(base_dir: Path | None = None) -> Path:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    return root / STORE_DIR / STORE_NAME


def _default_store() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "watchlists": []}


def _load_store(base_dir: Path | None = None) -> dict[str, Any]:
    path = _store_path(base_dir)
    if not path.exists():
        return _default_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_store()
    if not isinstance(payload, dict):
        return _default_store()
    watchlists = payload.get("watchlists")
    if not isinstance(watchlists, list):
        return _default_store()
    return {"schema_version": payload.get("schema_version", SCHEMA_VERSION), "watchlists": watchlists}


def _save_store(payload: dict[str, Any], base_dir: Path | None = None) -> Path:
    path = _store_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _normalize_symbols(symbols: Any) -> list[str]:
    if symbols is None:
        return []
    if not isinstance(symbols, list):
        raise ValueError("symbols must be a list of ticker strings")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in symbols:
        symbol = str(value or "").strip().upper()
        if not symbol:
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        normalized.append(symbol)
    return normalized


def _find_watchlist(store: dict[str, Any], state_key: str) -> dict[str, Any] | None:
    for item in store["watchlists"]:
        if item.get("state_key") == state_key:
            return item
    return None


def create_watchlist(payload: dict[str, Any], *, base_dir: Path | None = None) -> dict[str, Any]:
    requested_name = str(payload.get("name") or payload.get("workflow_state") or "").strip()
    if not requested_name:
        raise ValueError("create_watchlist requires 'name' or 'workflow_state'")

    workflow_state = normalize_workflow_state(requested_name)
    if workflow_state is None:
        allowed = ", ".join(workflow_state_labels())
        raise ValueError(f"unknown workflow state '{requested_name}'. allowed states: {allowed}")

    symbols = _normalize_symbols(payload.get("symbols"))
    note = str(payload.get("note") or "").strip()
    store = _load_store(base_dir)
    existing = _find_watchlist(store, workflow_state.key)
    if existing is not None:
        return {
            "status": "exists",
            "storage_path": str(_store_path(base_dir)),
            "watchlist": existing,
            "notes": [
                "Watchlists are workflow states, so each canonical state queue is unique.",
                "Returned existing watchlist instead of duplicating the workflow state.",
            ],
        }

    timestamp = _utc_now()
    watchlist = {
        "name": workflow_state.label,
        "workflow_state": workflow_state.label,
        "state_key": workflow_state.key,
        "allowed_next_states": list(workflow_state.allowed_next_states),
        "symbols": symbols,
        "note": note,
        "created_ts": timestamp,
        "updated_ts": timestamp,
    }
    store["watchlists"].append(watchlist)
    path = _save_store(store, base_dir)
    return {
        "status": "created",
        "storage_path": str(path),
        "watchlist": watchlist,
        "notes": [
            "Created a workflow-state watchlist queue.",
            "This is local SharpEdge bridge state, not a claimed public Robinhood watchlist API write.",
        ],
    }
