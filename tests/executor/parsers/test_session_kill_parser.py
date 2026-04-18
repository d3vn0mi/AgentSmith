"""Tests for the session_kill_parser."""
from __future__ import annotations

import time

from agent_smith.evidence.facts import KaliSession
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.session_kill_parser import SessionKillParser


def _run(stdout: str, exit_code: int = 0) -> ToolRun:
    return ToolRun(run_id="r", tool="tmux", command="...",
                    stdout=stdout, stderr="", exit_code=exit_code,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def _ctx(session_id: str = "sid-x"):
    return {"consumes": {"session": KaliSession.new(
        session_id=session_id, role="runner",
        status="live", kali_host="kali.lan")}}


def test_killed_line_emits_dead_session():
    facts = SessionKillParser().parse(_run("KILLED sid-x\n"),
                                        _ctx(session_id="sid-x"))
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "KaliSession"
    assert f.payload["session_id"] == "sid-x"
    assert f.payload["status"] == "dead"
    assert f.payload["role"] == "runner"
    assert f.payload["kali_host"] == "kali.lan"


def test_missing_killed_line_emits_nothing():
    facts = SessionKillParser().parse(_run("nothing here"), _ctx())
    assert facts == []


def test_no_session_in_context_emits_nothing():
    facts = SessionKillParser().parse(_run("KILLED sid-x\n"), context=None)
    assert facts == []
