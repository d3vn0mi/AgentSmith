"""Task and TaskState used by the Mission Graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_smith.evidence.facts import Fact


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


_ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.READY, TaskState.SKIPPED},
    TaskState.READY: {TaskState.AWAITING_APPROVAL, TaskState.RUNNING, TaskState.SKIPPED},
    TaskState.AWAITING_APPROVAL: {TaskState.RUNNING, TaskState.SKIPPED},
    TaskState.RUNNING: {TaskState.COMPLETE, TaskState.FAILED},
    TaskState.COMPLETE: set(),
    TaskState.FAILED: set(),
    TaskState.SKIPPED: set(),
}


@dataclass
class Task:
    id: str
    task_type: str
    args: dict[str, Any]
    consumes: dict[str, Fact]
    produces: list[str]
    state: TaskState = TaskState.PENDING
    triggered_by_rule: str | None = None
    triggered_by_fact_ids: list[str] = field(default_factory=list)
    parent_task_id: str | None = None
    created_at: float | None = None

    def transition(self, target: TaskState) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid transition: {self.state} -> {target}")
        self.state = target
