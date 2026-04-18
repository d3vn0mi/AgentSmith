"""Tests for the listener_parser (listener_start output)."""
from __future__ import annotations

import time

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.listener_parser import ListenerParser


def _run(stdout: str, stderr: str = "", exit_code: int = 0) -> ToolRun:
    return ToolRun(run_id="r", tool="tmux", command="...",
                    stdout=stdout, stderr=stderr, exit_code=exit_code,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def _ctx(kali_host: str = "kali.lan"):
    return {"args": {"kali_host": kali_host}}


def test_ready_line_emits_kalisession_and_shell():
    out = (
        "LISTENING agentsmith-abc12345-listen-99 10.10.14.7 4412\n"
        "CAUGHT agentsmith-abc12345-listen-99\n"
        "READY agentsmith-abc12345-listen-99 10.10.14.7 4412 www-data 1 10.129.0.1\n"
    )
    facts = ListenerParser().parse(_run(out), _ctx())
    assert len(facts) == 2
    by_type = {f.type: f for f in facts}
    assert "KaliSession" in by_type
    assert "Shell" in by_type

    ks = by_type["KaliSession"]
    assert ks.payload["session_id"] == "agentsmith-abc12345-listen-99"
    assert ks.payload["role"] == "shell"
    assert ks.payload["status"] == "live"
    assert ks.payload["kali_host"] == "kali.lan"

    sh = by_type["Shell"]
    assert sh.payload["session_id"] == "agentsmith-abc12345-listen-99"
    assert sh.payload["target_host"] == "10.129.0.1"
    assert sh.payload["listener_port"] == 4412
    assert sh.payload["callback_ip"] == "10.10.14.7"
    assert sh.payload["target_user"] == "www-data"
    assert sh.payload["interactive"] is True
    assert sh.payload["status"] == "live"


def test_ready_with_interactive_zero():
    out = "READY sid-1 10.10.14.7 4412 root 0 10.129.0.1\n"
    facts = ListenerParser().parse(_run(out), _ctx())
    by_type = {f.type: f for f in facts}
    assert by_type["Shell"].payload["interactive"] is False


def test_ready_with_unknown_target_ip():
    out = "READY sid-1 10.10.14.7 4412 root 1 unknown\n"
    facts = ListenerParser().parse(_run(out), _ctx())
    by_type = {f.type: f for f in facts}
    assert by_type["Shell"].payload["target_host"] == "unknown"


def test_fail_emits_nothing():
    facts = ListenerParser().parse(
        _run("", stderr="FAIL no callback in 120s\n", exit_code=2),
        _ctx(),
    )
    assert facts == []


def test_only_listening_no_ready_emits_nothing():
    out = "LISTENING sid 10.10.14.7 4412\n"
    facts = ListenerParser().parse(_run(out), _ctx())
    assert facts == []
