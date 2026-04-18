"""Tests for the MissionGraph data structure."""
from __future__ import annotations

import pytest

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.task import Task, TaskState


def _task(id_: str, state: TaskState = TaskState.PENDING) -> Task:
    t = Task(id=id_, task_type="x", args={}, consumes={}, produces=[])
    t.state = state
    return t


def test_add_task_and_retrieve():
    g = MissionGraph(mission_id="m1")
    t = _task("t1")
    g.add_task(t)
    assert g.get("t1") is t
    assert list(g.all_tasks()) == [t]


def test_add_duplicate_task_raises():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1"))
    with pytest.raises(ValueError):
        g.add_task(_task("t1"))


def test_by_state_filters():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.READY))
    g.add_task(_task("t2", TaskState.PENDING))
    g.add_task(_task("t3", TaskState.READY))
    ready = {t.id for t in g.by_state(TaskState.READY)}
    assert ready == {"t1", "t3"}


def test_edges_are_recorded_when_task_has_parent():
    g = MissionGraph(mission_id="m1")
    parent = _task("t1")
    g.add_task(parent)
    child = _task("t2")
    child.parent_task_id = "t1"
    g.add_task(child)
    assert g.children_of("t1") == ["t2"]
    assert g.parent_of("t2") == "t1"


def test_total_and_finished_counts():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.COMPLETE))
    g.add_task(_task("t2", TaskState.PENDING))
    g.add_task(_task("t3", TaskState.FAILED))
    g.add_task(_task("t4", TaskState.SKIPPED))
    assert g.total() == 4
    assert g.finished() == 3
