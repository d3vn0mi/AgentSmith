"""Tests for the shell runner wrapper."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_smith.executor.shell import ShellRunner
from agent_smith.transport.ssh import CommandResult


@dataclass
class FakeSSH:
    next_result: CommandResult
    last_cmd: str = ""
    last_timeout: int = 0

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_cmd = cmd
        self.last_timeout = timeout
        return self.next_result


@pytest.mark.asyncio
async def test_shell_runner_invokes_ssh_and_returns_toolrun():
    ssh = FakeSSH(next_result=CommandResult(
        command="echo hi", stdout="hi\n", stderr="", exit_code=0,
    ))
    runner = ShellRunner(ssh=ssh)
    run = await runner.run(tool="echo", command="echo hi", timeout=10)
    assert run.tool == "echo"
    assert run.command == "echo hi"
    assert run.stdout == "hi\n"
    assert run.exit_code == 0
    assert run.duration_ms >= 0
    assert run.timed_out is False
    assert ssh.last_cmd == "echo hi"
    assert ssh.last_timeout == 10


@pytest.mark.asyncio
async def test_shell_runner_preserves_timeout_flag():
    ssh = FakeSSH(next_result=CommandResult(
        command="sleep 100", stdout="", stderr="timed out", exit_code=None, timed_out=True,
    ))
    runner = ShellRunner(ssh=ssh)
    run = await runner.run(tool="sleep", command="sleep 100", timeout=1)
    assert run.timed_out is True
    assert run.exit_code is None


@pytest.mark.asyncio
async def test_shell_runner_generates_unique_run_ids():
    ssh = FakeSSH(next_result=CommandResult(
        command="x", stdout="", stderr="", exit_code=0,
    ))
    runner = ShellRunner(ssh=ssh)
    r1 = await runner.run(tool="x", command="x")
    r2 = await runner.run(tool="x", command="x")
    assert r1.run_id != r2.run_id
