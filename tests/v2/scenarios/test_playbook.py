"""Tests for playbook dataclasses."""
from __future__ import annotations

from agent_smith.scenarios.playbook import (
    ExpansionRule,
    Playbook,
    RootTaskSpec,
    TaskTypeSpec,
    TerminationRule,
)


def test_playbook_defaults_are_empty():
    p = Playbook(name="x", version="1.0")
    assert p.root_tasks == []
    assert p.task_types == {}
    assert p.expansions == []
    assert p.terminations == []
    assert p.cost_cap_usd is None


def test_task_type_spec_round_trip():
    spec = TaskTypeSpec(
        name="port_scan",
        consumes={"host": "Host"},
        produces=["OpenPort"],
        tool="nmap",
        args_template={"target": "{host.ip}"},
        risk="low",
        timeout=300,
        parser="nmap",
    )
    assert spec.name == "port_scan"
    assert spec.consumes == {"host": "Host"}


def test_expansion_rule_fields():
    rule = ExpansionRule(id="r1", on_fact="OpenPort{service: http}", spawn=["web_dir_enum"])
    assert rule.id == "r1"
    assert rule.spawn == ["web_dir_enum"]


def test_termination_rule_named():
    tr = TerminationRule(kind="scope_exhausted")
    assert tr.kind == "scope_exhausted"


def test_root_task_spec_carries_args():
    r = RootTaskSpec(task_type="port_scan", args={"host_set": ["1.2.3.4"]})
    assert r.task_type == "port_scan"
    assert r.args["host_set"] == ["1.2.3.4"]
