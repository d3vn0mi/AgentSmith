"""Tests for the Executor."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_smith.executor.executor import Executor
from agent_smith.graph.task import Task, TaskState
from agent_smith.scenarios.playbook import TaskTypeSpec
from agent_smith.transport.ssh import CommandResult


@dataclass
class FakeSSH:
    stdout: str = ""
    last_cmd: str = ""

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_cmd = cmd
        return CommandResult(command=cmd, stdout=self.stdout, stderr="", exit_code=0)


def _nmap_builder(spec, args):
    return f"nmap -sV -oX - {args['target']}"


@pytest.fixture
def port_scan_spec() -> TaskTypeSpec:
    return TaskTypeSpec(
        name="port_scan",
        consumes={},
        produces=["Host", "OpenPort"],
        tool="nmap",
        args_template={"target": "{target}"},
        parser="nmap",
        timeout=60,
    )


@pytest.mark.asyncio
async def test_executor_resolves_template_args(port_scan_spec, tmp_path: Path):
    ssh = FakeSSH(stdout="<?xml version='1.0'?><nmaprun/>")
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    assert "203.0.113.10" in ssh.last_cmd
    assert result.tool_run.exit_code == 0


@pytest.mark.asyncio
async def test_executor_runs_parser_when_registered(port_scan_spec, tmp_path: Path):
    nmap_xml = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/><address addr="203.0.113.10" addrtype="ipv4"/><ports>
<port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
</ports></host></nmaprun>"""
    ssh = FakeSSH(stdout=nmap_xml)
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    kinds = {f.type for f in result.facts}
    assert "Host" in kinds
    assert "OpenPort" in kinds


@pytest.mark.asyncio
async def test_executor_writes_stdout_file(port_scan_spec, tmp_path: Path):
    ssh = FakeSSH(stdout="<?xml version='1.0'?><nmaprun/>")
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    stdout_file = tmp_path / "tool_runs" / f"{result.tool_run.run_id}.stdout"
    assert stdout_file.exists()
    assert "nmaprun" in stdout_file.read_text()


def test_default_command_builder_handles_prerendered_args():
    """Spawned tasks have args pre-rendered by _render_args; the default
    builder must not try to re-render template placeholders."""
    from agent_smith.executor.executor import default_command_builder
    spec = TaskTypeSpec(
        name="web_probe",
        consumes={"host": "Host", "port": "OpenPort{service: http|https}"},
        produces=[],
        tool="curl",
        args_template={"url": "http://{host.ip}:{port.number}"},
    )
    args = {"url": "http://10.0.0.5:80"}  # already rendered by controller
    cmd = default_command_builder(spec, args)
    assert "curl" in cmd
    assert "--url=http://10.0.0.5:80" in cmd
