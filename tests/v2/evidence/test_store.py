"""Tests for the EvidenceStore: dedup, supersede, queries, subscriptions."""
from __future__ import annotations

from agent_smith.evidence.facts import Host, OpenPort, Provenance
from agent_smith.evidence.matcher import parse_predicate
from agent_smith.evidence.store import EvidenceStore


def _prov(task: str = "t1") -> Provenance:
    return Provenance(
        task_id=task, tool_run_id="r1", parser="nmap", timestamp=0.0, snippet="x"
    )


def test_insert_new_fact_stores_it():
    s = EvidenceStore()
    f = Host.new(ip="1.2.3.4")
    f.append_provenance(_prov())
    result = s.insert(f)
    assert result.inserted is True
    assert result.fact is f
    assert len(s.all()) == 1


def test_insert_duplicate_key_merges_provenance():
    s = EvidenceStore()
    first = Host.new(ip="1.2.3.4")
    first.append_provenance(_prov("t1"))
    s.insert(first)

    second = Host.new(ip="1.2.3.4")
    second.append_provenance(_prov("t2"))
    result = s.insert(second)

    assert result.inserted is False
    assert result.fact.id == first.id
    assert len(result.fact.provenance) == 2


def test_supersede_when_payload_materially_differs():
    s = EvidenceStore()
    first = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    s.insert(first)

    second = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh", version="OpenSSH 8.9")
    result = s.insert(second)

    assert result.superseded is True
    assert first.superseded_by is not None
    live = s.by_type("OpenPort")
    assert len(live) == 1
    assert live[0].payload["version"] == "OpenSSH 8.9"


def test_by_type_only_returns_live_facts():
    s = EvidenceStore()
    f1 = Host.new(ip="1.2.3.4")
    f2 = Host.new(ip="5.6.7.8")
    s.insert(f1)
    s.insert(f2)
    assert {f.payload["ip"] for f in s.by_type("Host")} == {"1.2.3.4", "5.6.7.8"}


def test_by_predicate_returns_matching_live_facts():
    s = EvidenceStore()
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))

    web = s.by_predicate(parse_predicate("OpenPort{service: http|https}"))
    assert {f.payload["number"] for f in web} == {80, 443}


def test_subscribe_on_insert_invoked():
    s = EvidenceStore()
    seen = []
    s.on_insert(lambda result: seen.append(result))
    s.insert(Host.new(ip="1.2.3.4"))
    assert len(seen) == 1
    assert seen[0].inserted is True


def test_subscribe_on_supersede_also_invoked_on_update():
    s = EvidenceStore()
    events = []
    s.on_insert(lambda r: events.append(("insert", r.inserted, r.superseded)))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh", version="OpenSSH 8.9"))
    assert events == [("insert", True, False), ("insert", False, True)]
