"""Phase 1 serial scheduler.

Picks the first READY task in insertion order. Concurrency, OPSEC rate
limiting, and cost-aware scheduling arrive in Phase 2.
"""
from __future__ import annotations

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.task import Task, TaskState


_OUTSTANDING = {TaskState.PENDING, TaskState.READY, TaskState.AWAITING_APPROVAL, TaskState.RUNNING}


class Scheduler:
    def __init__(self, graph: MissionGraph) -> None:
        self.graph = graph

    def next_ready(self) -> Task | None:
        for t in self.graph.all_tasks():
            if t.state == TaskState.READY:
                return t
        return None

    def has_outstanding_work(self) -> bool:
        return any(t.state in _OUTSTANDING for t in self.graph.all_tasks())
