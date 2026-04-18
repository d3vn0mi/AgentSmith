"""MissionGraph: typed tasks as nodes, parent->child as edges."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agent_smith.graph.task import Task, TaskState


_FINISHED = {TaskState.COMPLETE, TaskState.FAILED, TaskState.SKIPPED}


class MissionGraph:
    def __init__(self, mission_id: str) -> None:
        self.mission_id = mission_id
        self._tasks: dict[str, Task] = {}
        self._children: dict[str, list[str]] = {}

    def add_task(self, task: Task) -> None:
        if task.id in self._tasks:
            raise ValueError(f"duplicate task id: {task.id}")
        self._tasks[task.id] = task
        self._children.setdefault(task.id, [])
        if task.parent_task_id:
            self._children.setdefault(task.parent_task_id, []).append(task.id)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> Iterable[Task]:
        return self._tasks.values()

    def by_state(self, state: TaskState) -> list[Task]:
        return [t for t in self._tasks.values() if t.state == state]

    def children_of(self, task_id: str) -> list[str]:
        return list(self._children.get(task_id, []))

    def parent_of(self, task_id: str) -> str | None:
        t = self._tasks.get(task_id)
        return t.parent_task_id if t else None

    def total(self) -> int:
        return len(self._tasks)

    def finished(self) -> int:
        return sum(1 for t in self._tasks.values() if t.state in _FINISHED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "total": self.total(),
            "finished": self.finished(),
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "state": t.state.value,
                    "parent_task_id": t.parent_task_id,
                    "triggered_by_rule": t.triggered_by_rule,
                    "args": t.args,
                }
                for t in self._tasks.values()
            ],
        }
