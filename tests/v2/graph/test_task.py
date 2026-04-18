"""Tests for Task and TaskState."""
from __future__ import annotations

import pytest

from agent_smith.graph.task import Task, TaskState


def test_task_starts_pending():
    t = Task(
        id="t1",
        task_type="port_scan",
        args={"host": "1.2.3.4"},
        consumes={},
        produces=["Host", "OpenPort"],
    )
    assert t.state == TaskState.PENDING


def test_transition_allowed_pending_to_ready():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    t.transition(TaskState.READY)
    assert t.state == TaskState.READY


def test_transition_disallowed_pending_to_complete():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    with pytest.raises(ValueError):
        t.transition(TaskState.COMPLETE)


def test_full_happy_path():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    for s in [TaskState.READY, TaskState.RUNNING, TaskState.COMPLETE]:
        t.transition(s)
    assert t.state == TaskState.COMPLETE
