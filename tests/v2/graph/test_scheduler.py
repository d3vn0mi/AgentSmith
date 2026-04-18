"""Tests for the Phase 1 serial scheduler."""
from __future__ import annotations

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.scheduler import Scheduler
from agent_smith.graph.task import Task, TaskState


def _task(id_: str, state: TaskState = TaskState.PENDING) -> Task:
    t = Task(id=id_, task_type="x", args={}, consumes={}, produces=[])
    t.state = state
    return t


def test_next_ready_returns_first_ready_task():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.COMPLETE))
    g.add_task(_task("t2", TaskState.READY))
    g.add_task(_task("t3", TaskState.READY))
    s = Scheduler(g)
    picked = s.next_ready()
    assert picked is not None
    assert picked.id == "t2"


def test_next_ready_returns_none_when_no_ready_tasks():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.PENDING))
    s = Scheduler(g)
    assert s.next_ready() is None


def test_has_outstanding_work_respects_pending_and_running():
    g = MissionGraph(mission_id="m1")
    s = Scheduler(g)
    assert not s.has_outstanding_work()

    g.add_task(_task("t1", TaskState.PENDING))
    assert s.has_outstanding_work()

    g.get("t1").state = TaskState.COMPLETE
    assert not s.has_outstanding_work()
