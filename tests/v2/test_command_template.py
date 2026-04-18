"""Tests for the command_template override on TaskTypeSpec."""
from __future__ import annotations

from agent_smith.executor.executor import default_command_builder
from agent_smith.scenarios.playbook import TaskTypeSpec


def _spec(**kwargs) -> TaskTypeSpec:
    defaults = dict(
        name="t", consumes={}, produces=[], tool="dummy",
        args_template={}, timeout=60, parser=None,
    )
    defaults.update(kwargs)
    return TaskTypeSpec(**defaults)


def test_command_template_renders_with_args():
    spec = _spec(
        tool="nmap",
        command_template="nmap -sV -T4 -oX - {target}",
        args_template={"target": "{target}"},
    )
    cmd = default_command_builder(spec, {"target": "10.0.0.1"})
    assert cmd == "nmap -sV -T4 -oX - 10.0.0.1"


def test_command_template_falls_back_to_kv_when_absent():
    spec = _spec(
        tool="nmap",
        args_template={"target": "{target}"},
    )
    cmd = default_command_builder(spec, {"target": "10.0.0.1"})
    assert cmd == "nmap --target=10.0.0.1"
