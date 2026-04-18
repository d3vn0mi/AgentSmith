"""Tests for the kali_session_parser (session_start output)."""
from __future__ import annotations

import time

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.kali_session_parser import KaliSessionParser


def _run(stdout: str, stderr: str = "", exit_code: int = 0) -> ToolRun:
    return ToolRun(run_id="r", tool="tmux", command="...",
                    stdout=stdout, stderr=stderr, exit_code=exit_code,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def _ctx(role: str = "runner", kali_host: str = "10.0.0.5"):
    return {"args": {"role": role, "kali_host": kali_host}}


def test_ok_line_emits_session():
    out = "OK agentsmith-abc12345-runner-1234\n"
    facts = KaliSessionParser().parse(_run(out), _ctx())
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "KaliSession"
    assert f.payload["session_id"] == "agentsmith-abc12345-runner-1234"
    assert f.payload["role"] == "runner"
    assert f.payload["status"] == "live"
    assert f.payload["kali_host"] == "10.0.0.5"


def test_fail_line_emits_nothing():
    out = ""
    facts = KaliSessionParser().parse(
        _run(out, stderr="FAIL agentsmith-abc-runner-1\n", exit_code=1),
        _ctx(),
    )
    assert facts == []


def test_malformed_output_emits_nothing():
    facts = KaliSessionParser().parse(_run("gibberish here"), _ctx())
    assert facts == []


def test_missing_context_uses_defaults():
    """Parser tolerates missing context keys."""
    out = "OK agentsmith-x-runner-1\n"
    facts = KaliSessionParser().parse(_run(out), context=None)
    assert len(facts) == 1
    assert facts[0].payload["role"] == ""
    assert facts[0].payload["kali_host"] == ""
