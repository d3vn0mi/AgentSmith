"""Verifies Parser.parse receives context from the Executor."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agent_smith.evidence.facts import Fact
from agent_smith.executor.executor import Executor
from agent_smith.executor.parsers import register, reset_for_tests
from agent_smith.executor.parsers.base import Parser, ToolRun
from agent_smith.graph.task import Task
from agent_smith.scenarios.playbook import TaskTypeSpec


class _CapturingParser:
    tool = "capture"
    captured: dict | None = None

    def parse(self, run: ToolRun, context=None):
        _CapturingParser.captured = context
        return []


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield
    reset_for_tests()


@pytest.mark.asyncio
async def test_executor_passes_consumes_as_context(tmp_path):
    _CapturingParser.captured = None
    register(_CapturingParser())

    class _FakeSsh:
        async def run_command(self, cmd, timeout=60):
            class R:
                stdout = ""
                stderr = ""
                exit_code = 0
                timed_out = False
            return R()

    ex = Executor(ssh=_FakeSsh(), run_dir=tmp_path)
    spec = TaskTypeSpec(
        name="t", consumes={"tech": "WebTech"}, produces=[],
        tool="capture", args_template={}, timeout=30, parser="capture",
        command_template="echo hi",
    )
    fact = Fact(type="WebTech", payload={"software": "WordPress"},
                 canonical_key="tech:h:80:wordpress")

    # Task dataclass: id, task_type, args, consumes, produces (all required except state etc.)
    task = Task(id="t1", task_type="t", args={},
                consumes={"tech": fact}, produces=[])

    await ex.run(task, spec)

    assert _CapturingParser.captured == {"consumes": {"tech": fact}, "args": {}}
