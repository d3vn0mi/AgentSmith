"""Tests for the expansion engine."""
from __future__ import annotations

from agent_smith.evidence.facts import Host, OpenPort
from agent_smith.scenarios.expansion import ExpansionEngine, SpawnRequest
from agent_smith.scenarios.playbook import ExpansionRule, Playbook, TaskTypeSpec


def _playbook_with_web_rule() -> Playbook:
    return Playbook(
        name="x",
        version="1.0",
        task_types={
            "web_dir_enum": TaskTypeSpec(
                name="web_dir_enum",
                consumes={"host": "Host", "port": "OpenPort{service: http|https}"},
                produces=["WebEndpoint"],
                tool="feroxbuster",
                args_template={"url": "https://{host.ip}:{port.number}"},
            ),
        },
        expansions=[
            ExpansionRule(
                id="http-enum",
                on_fact="OpenPort{service: http|https}",
                spawn=["web_dir_enum"],
            ),
        ],
    )


def test_matching_fact_spawns_requested_task_types():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    host = Host.new(ip="1.2.3.4")
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    spawns = eng.on_fact(port, known_facts=[host, port])
    assert len(spawns) == 1
    s: SpawnRequest = spawns[0]
    assert s.task_type == "web_dir_enum"
    assert s.rule_id == "http-enum"
    assert s.triggered_by_fact_id == port.id


def test_non_matching_fact_spawns_nothing():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    ssh = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    assert eng.on_fact(ssh, known_facts=[ssh]) == []


def test_spawn_skipped_when_required_consume_missing():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    spawns = eng.on_fact(port, known_facts=[port])
    assert spawns == []


def test_spawn_request_carries_resolved_consume_map():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    host = Host.new(ip="1.2.3.4")
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    [spawn] = eng.on_fact(port, known_facts=[host, port])
    assert spawn.consumes["host"] is host
    assert spawn.consumes["port"] is port
