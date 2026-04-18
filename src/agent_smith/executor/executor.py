"""Executor: dispatches a Task.

Responsibilities:
  1. Build the command from the TaskTypeSpec's args_template + task.args.
  2. Run via ShellRunner.
  3. Persist stdout/stderr to disk (run_dir/tool_runs/{run_id}.{stdout,stderr}).
  4. Route the resulting ToolRun through the registered parser, if any.
  5. Return a TaskExecutionResult with the ToolRun and emitted facts.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_smith.evidence.facts import Fact
from agent_smith.executor.parsers import get_parser
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.shell import ShellRunner
from agent_smith.graph.task import Task
from agent_smith.scenarios.playbook import TaskTypeSpec


class _SshLike(Protocol):
    async def run_command(self, cmd: str, timeout: int = 60): ...


@dataclass
class TaskExecutionResult:
    tool_run: ToolRun
    facts: list[Fact]


CommandBuilder = Callable[[TaskTypeSpec, dict[str, Any]], str]


def default_command_builder(spec: TaskTypeSpec, args: dict[str, Any]) -> str:
    """Render args_template keys as --key=value pairs, using already-resolved args.

    By the time the Executor calls this, `args` has been rendered by
    MissionController._render_args (for spawned tasks) or carries root-task
    literal values. The template keys in spec.args_template identify which
    args are meaningful; values come from `args`.
    """
    parts: list[str] = [spec.tool]
    for key in spec.args_template.keys():
        if key in args:
            parts.append(f"--{key}={args[key]}")
    return " ".join(parts)


class Executor:
    def __init__(
        self,
        ssh: _SshLike,
        run_dir: Path,
        command_builder: CommandBuilder = default_command_builder,
    ) -> None:
        self.runner = ShellRunner(ssh)
        self.run_dir = run_dir
        self.tool_runs_dir = run_dir / "tool_runs"
        self.tool_runs_dir.mkdir(parents=True, exist_ok=True)
        self.command_builder = command_builder

    async def run(self, task: Task, spec: TaskTypeSpec) -> TaskExecutionResult:
        command = self.command_builder(spec, task.args)
        tool_run = await self.runner.run(tool=spec.tool, command=command, timeout=spec.timeout)
        self._persist(tool_run)
        facts: list[Fact] = []
        if spec.parser:
            parser = get_parser(spec.parser)
            if parser is not None:
                facts = parser.parse(tool_run)
                for f in facts:
                    for prov in f.provenance:
                        if prov.task_id == "":
                            prov.task_id = task.id
        return TaskExecutionResult(tool_run=tool_run, facts=facts)

    def _persist(self, run: ToolRun) -> None:
        (self.tool_runs_dir / f"{run.run_id}.stdout").write_text(run.stdout)
        (self.tool_runs_dir / f"{run.run_id}.stderr").write_text(run.stderr)
