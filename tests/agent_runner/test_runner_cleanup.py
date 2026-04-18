"""Tests for _cleanup_kali_sessions in the v2 runner."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent_smith.agent_runner.runner import _cleanup_kali_sessions


@pytest.mark.asyncio
async def test_runs_tmux_cleanup_command_with_mission_prefix():
    ssh = AsyncMock()
    ssh.run_command = AsyncMock()
    await _cleanup_kali_sessions("7be2bc45-deadbeef", ssh)
    assert ssh.run_command.await_count == 1
    cmd = ssh.run_command.await_args.args[0]
    assert "agentsmith-7be2bc45-" in cmd
    assert "tmux kill-session" in cmd
    assert "tmux ls" in cmd


@pytest.mark.asyncio
async def test_silent_when_ssh_raises():
    ssh = AsyncMock()
    ssh.run_command = AsyncMock(side_effect=RuntimeError("ssh gone"))
    # Must not raise.
    await _cleanup_kali_sessions("m", ssh)
