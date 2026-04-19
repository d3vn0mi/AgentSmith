"""Verify the openadmin_demo playbook loads via the v2 loader."""
from __future__ import annotations

from pathlib import Path

from agent_smith.scenarios.loader import load_playbook


PB = Path("src/agent_smith/playbooks/openadmin_demo.yaml")


def test_openadmin_demo_loads():
    pb = load_playbook(PB)
    assert pb.name == "openadmin-demo"
    assert "exploit_openadmin" in pb.task_types
    t = pb.task_types["exploit_openadmin"]
    assert t.parser == "listener"
    assert t.tool == "tmux"
    assert "xajaxargs[]=ip=>" in t.command_template
    assert "--data-urlencode" in t.command_template


def test_openadmin_demo_root_references_agent_config():
    pb = load_playbook(PB)
    assert len(pb.root_tasks) == 1
    root = pb.root_tasks[0]
    assert root.task_type == "exploit_openadmin"
    assert root.args["target_port"] == "${AGENT_CONFIG:target_port}"
    assert root.args["ona_path"] == "${AGENT_CONFIG:ona_path}"
    assert root.args["target_host"] == "${TARGET}"
