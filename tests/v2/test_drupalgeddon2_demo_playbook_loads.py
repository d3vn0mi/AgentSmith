"""Verify the drupalgeddon2_demo playbook loads via the v2 loader."""
from __future__ import annotations

from pathlib import Path

from agent_smith.scenarios.loader import load_playbook


PB = Path("src/agent_smith/playbooks/drupalgeddon2_demo.yaml")


def test_drupalgeddon2_demo_loads():
    pb = load_playbook(PB)
    assert pb.name == "drupalgeddon2-demo"
    assert "exploit_drupalgeddon2" in pb.task_types
    t = pb.task_types["exploit_drupalgeddon2"]
    assert t.parser == "listener"
    assert t.tool == "tmux"
    assert "mail[#markup]" in t.command_template
    assert "--data-urlencode" in t.command_template
    assert "/user/register" in t.command_template


def test_drupalgeddon2_demo_root_references_agent_config():
    pb = load_playbook(PB)
    assert len(pb.root_tasks) == 1
    root = pb.root_tasks[0]
    assert root.task_type == "exploit_drupalgeddon2"
    assert root.args["target_port"] == "${AGENT_CONFIG:target_port}"
    assert root.args["drupal_path"] == "${AGENT_CONFIG:drupal_path}"
    assert root.args["target_host"] == "${TARGET}"
