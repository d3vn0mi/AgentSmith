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
