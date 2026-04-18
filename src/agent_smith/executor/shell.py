"""Thin wrapper around SSHConnection producing a ToolRun."""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from agent_smith.executor.parsers.base import ToolRun


class _SshLike(Protocol):
    async def run_command(self, cmd: str, timeout: int = 60): ...


class ShellRunner:
    def __init__(self, ssh: _SshLike) -> None:
        self.ssh = ssh

    async def run(self, tool: str, command: str, timeout: int = 60) -> ToolRun:
        run_id = str(uuid.uuid4())
        started_at = time.time()
        result = await self.ssh.run_command(command, timeout=timeout)
        finished_at = time.time()
        return ToolRun(
            run_id=run_id,
            tool=tool,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=int((finished_at - started_at) * 1000),
            started_at=started_at,
            finished_at=finished_at,
            timed_out=result.timed_out,
        )
