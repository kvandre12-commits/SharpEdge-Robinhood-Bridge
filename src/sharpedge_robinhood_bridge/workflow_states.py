from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowState:
    key: str
    label: str
    allowed_next_states: tuple[str, ...]


WORKFLOW_STATES: tuple[WorkflowState, ...] = (
    WorkflowState("research", "Research", ("Candidate",)),
    WorkflowState("candidate", "Candidate", ("High Conviction",)),
    WorkflowState("high_conviction", "High Conviction", ("Execution Queue",)),
    WorkflowState("execution_queue", "Execution Queue", ("Order Review",)),
    WorkflowState("order_review", "Order Review", ("Order Placement",)),
    WorkflowState("order_placement", "Order Placement", ()),
)

_STATE_BY_KEY = {state.key: state for state in WORKFLOW_STATES}
_ALIAS_TO_KEY = {
    "research": "research",
    "candidate": "candidate",
    "high conviction": "high_conviction",
    "high_conviction": "high_conviction",
    "high-conviction": "high_conviction",
    "execution queue": "execution_queue",
    "execution_queue": "execution_queue",
    "execution-queue": "execution_queue",
    "order review": "order_review",
    "order_review": "order_review",
    "order-review": "order_review",
    "order placement": "order_placement",
    "order_placement": "order_placement",
    "order-placement": "order_placement",
}


def normalize_workflow_state(value: str) -> WorkflowState | None:
    normalized = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    state_key = _ALIAS_TO_KEY.get(normalized) or _ALIAS_TO_KEY.get(normalized.replace(" ", "_"))
    if state_key is None:
        return None
    return _STATE_BY_KEY[state_key]


def workflow_state_labels() -> list[str]:
    return [state.label for state in WORKFLOW_STATES]


def workflow_state_order(state_key: str) -> int:
    for index, state in enumerate(WORKFLOW_STATES):
        if state.key == state_key:
            return index
    return len(WORKFLOW_STATES)
