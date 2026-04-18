"""Verifies Executor passes task.args in context alongside task.consumes."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_smith.executor.executor import Executor
from agent_smith.executor.parsers import register, reset_for_tests
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.graph.task import Task
from agent_smith.scenarios.playbook import TaskTypeSpec


class _CapturingParser:
    tool = "args_capture"
    last_context: dict | None = None

    def parse(self, run: ToolRun, context=None):
        _CapturingParser.last_context = context
        return []


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


class _FakeSsh:
    async def run_command(self, cmd, timeout=60):
        class R:
            stdout = ""
            stderr = ""
            exit_code = 0
            timed_out = False
        return R()


@pytest.mark.asyncio
async def test_executor_passes_args_in_context(tmp_path):
    _CapturingParser.last_context = None
    register(_CapturingParser())
    ex = Executor(ssh=_FakeSsh(), run_dir=tmp_path)
    spec = TaskTypeSpec(
        name="t", consumes={}, produces=[], tool="args_capture",
        args_template={}, timeout=30, parser="args_capture",
        command_template="echo hi",
    )
    task = Task(
        id="t1", task_type="t", args={"role": "runner", "kali_host": "k"},
        consumes={}, produces=[],
    )
    await ex.run(task, spec)

    ctx = _CapturingParser.last_context
    assert ctx is not None
    assert ctx["consumes"] == {}
    assert ctx["args"] == {"role": "runner", "kali_host": "k"}
