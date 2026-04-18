"""Tests for the session_exec_parser (liveness + stdout passthrough)."""
from __future__ import annotations

import time

from agent_smith.evidence.facts import KaliSession, Shell
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.session_exec_parser import SessionExecParser


def _run(stdout: str, stderr: str = "", exit_code: int = 0) -> ToolRun:
    return ToolRun(run_id="r", tool="tmux", command="...",
                    stdout=stdout, stderr=stderr, exit_code=exit_code,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def _ctx_with_session(session_id: str = "sid-x",
                       kali_host: str = "kali.lan",
                       with_shell: bool = False):
    session_fact = KaliSession.new(
        session_id=session_id, role="shell",
        status="live", kali_host=kali_host,
    )
    consumes = {"session": session_fact}
    if with_shell:
        consumes["shell"] = Shell.new(
            session_id=session_id, target_host="10.0.0.1",
            listener_port=4400, callback_ip="10.10.14.7",
            status="live",
        )
    return {"consumes": consumes}


def test_normal_output_emits_no_facts():
    facts = SessionExecParser().parse(_run("hello\nbob\n"),
                                        _ctx_with_session())
    assert facts == []


def test_dead_session_supersedes_with_dead_status():
    facts = SessionExecParser().parse(
        _run("", stderr="DEAD sid-x\n", exit_code=4),
        _ctx_with_session(session_id="sid-x"),
    )
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "KaliSession"
    assert f.payload["session_id"] == "sid-x"
    assert f.payload["status"] == "dead"
    assert f.payload["role"] == "shell"  # role preserved from consumed fact


def test_dead_session_also_supersedes_matching_shell():
    facts = SessionExecParser().parse(
        _run("", stderr="DEAD sid-x\n", exit_code=4),
        _ctx_with_session(session_id="sid-x", with_shell=True),
    )
    assert len(facts) == 2
    by_type = {f.type: f for f in facts}
    assert by_type["KaliSession"].payload["status"] == "dead"
    assert by_type["Shell"].payload["status"] == "dead"


def test_exec_timeout_emits_nothing():
    """FAIL exec timeout keeps the session live — no facts supersede."""
    facts = SessionExecParser().parse(
        _run("partial output", stderr="FAIL exec timeout\n", exit_code=3),
        _ctx_with_session(),
    )
    assert facts == []


def test_missing_context_tolerated():
    facts = SessionExecParser().parse(_run("ok"), context=None)
    assert facts == []
