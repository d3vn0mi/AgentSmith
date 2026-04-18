"""Tests for the Fact base class and Provenance."""
from __future__ import annotations

import time

from agent_smith.evidence.facts import Fact, Provenance


def test_provenance_carries_task_run_parser_timestamp():
    p = Provenance(
        task_id="t1",
        tool_run_id="r1",
        parser="nmap",
        timestamp=123.0,
        snippet="22/tcp open ssh",
    )
    assert p.task_id == "t1"
    assert p.parser == "nmap"


def test_fact_base_defaults_id_confidence_timestamps():
    f = Fact(
        type="Host",
        payload={"ip": "1.2.3.4"},
        canonical_key="host:1.2.3.4",
    )
    assert f.id  # uuid generated
    assert f.confidence == 1.0
    assert f.superseded_by is None
    assert f.created_at <= time.time() + 1
    assert f.last_seen_at <= time.time() + 1


def test_fact_append_provenance_bumps_last_seen():
    f = Fact(type="Host", payload={"ip": "1.2.3.4"}, canonical_key="host:1.2.3.4")
    earlier = f.last_seen_at
    time.sleep(0.01)
    f.append_provenance(
        Provenance(task_id="t1", tool_run_id="r1", parser="nmap", timestamp=time.time(), snippet="x")
    )
    assert f.last_seen_at > earlier
    assert len(f.provenance) == 1


from agent_smith.evidence.facts import Host, OpenPort, WebEndpoint


def test_host_fact_canonical_key_is_ip():
    h = Host.new(ip="10.0.0.5", hostname="srv", alive=True)
    assert h.type == "Host"
    assert h.canonical_key == "host:10.0.0.5"
    assert h.payload == {"ip": "10.0.0.5", "hostname": "srv", "os": None, "alive": True}


def test_host_fact_alive_defaults_true():
    h = Host.new(ip="10.0.0.5")
    assert h.payload["alive"] is True
    assert h.payload["hostname"] is None


def test_open_port_canonical_key_includes_protocol_and_number():
    p = OpenPort.new(host_ip="10.0.0.5", number=22, protocol="tcp", service="ssh")
    assert p.type == "OpenPort"
    assert p.canonical_key == "port:10.0.0.5:tcp:22"
    assert p.payload["service"] == "ssh"
    assert p.payload["version"] is None


def test_open_port_defaults_protocol_tcp():
    p = OpenPort.new(host_ip="10.0.0.5", number=80)
    assert p.payload["protocol"] == "tcp"
    assert p.payload["service"] is None


def test_web_endpoint_canonical_key_is_url():
    e = WebEndpoint.new(url="https://site/x", status=200, title="Admin", interesting=True)
    assert e.type == "WebEndpoint"
    assert e.canonical_key == "web:https://site/x"
    assert e.payload["title"] == "Admin"
    assert e.payload["interesting"] is True


def test_web_endpoint_interesting_defaults_false():
    e = WebEndpoint.new(url="https://site/x", status=404)
    assert e.payload["interesting"] is False
