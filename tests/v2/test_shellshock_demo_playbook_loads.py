"""Verify the shellshock_demo playbook loads via the v2 loader."""
from __future__ import annotations

from pathlib import Path

from agent_smith.scenarios.loader import load_playbook


PB = Path("src/agent_smith/playbooks/shellshock_demo.yaml")


def test_shellshock_demo_loads():
    pb = load_playbook(PB)
    assert pb.name == "shellshock-demo"
    assert "exploit_shellshock" in pb.task_types
    t = pb.task_types["exploit_shellshock"]
    assert t.parser == "listener"
    assert t.tool == "tmux"
    assert "User-Agent" in t.command_template
    assert "/bin/bash" in t.command_template
    assert "curl" in t.command_template


def test_shellshock_demo_root_references_agent_config():
    pb = load_playbook(PB)
    assert len(pb.root_tasks) == 1
    root = pb.root_tasks[0]
    assert root.task_type == "exploit_shellshock"
    # Root args must reference ${AGENT_CONFIG:...} for target_port and cgi_path
    # so operators can parameterize per mission.
    assert root.args["target_port"] == "${AGENT_CONFIG:target_port}"
    assert root.args["cgi_path"] == "${AGENT_CONFIG:cgi_path}"
    assert root.args["target_host"] == "${TARGET}"
