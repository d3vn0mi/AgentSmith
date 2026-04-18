"""Verify the Phase C demo playbooks load via the v2 loader."""
from __future__ import annotations

from pathlib import Path

from agent_smith.scenarios.loader import load_playbook


SESSION_DEMO = Path("src/agent_smith/playbooks/kali_session_demo.yaml")
REV_SHELL_DEMO = Path("src/agent_smith/playbooks/reverse_shell_demo.yaml")


def test_kali_session_demo_loads():
    pb = load_playbook(SESSION_DEMO)
    assert pb.name == "kali-session-demo"
    assert set(pb.task_types) == {"session_start", "session_exec", "session_kill"}
    assert pb.task_types["session_start"].parser == "kali_session"
    assert pb.task_types["session_exec"].parser == "session_exec"
    assert pb.task_types["session_kill"].parser == "session_kill"


def test_reverse_shell_demo_loads():
    pb = load_playbook(REV_SHELL_DEMO)
    assert pb.name == "reverse-shell-demo"
    assert "listener_start" in pb.task_types
    assert pb.task_types["listener_start"].parser == "listener"
