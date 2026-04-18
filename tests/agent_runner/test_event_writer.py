"""Tests for the agent's JSONL event writer."""
from __future__ import annotations

import json

from agent_smith.agent_runner.event_writer import EventWriter


def test_seq_is_monotonic(tmp_path):
    w = EventWriter(tmp_path / "events.jsonl",
                     mission_id="m1", agent_id="a1")
    w.emit("mission.started", {})
    w.emit("agent.thinking", {"reasoning": "hm"})
    w.close()

    lines = (tmp_path / "events.jsonl").read_text().strip().splitlines()
    events = [json.loads(l) for l in lines]
    assert [e["seq"] for e in events] == [0, 1]
    assert events[0]["type"] == "mission.started"
    assert events[0]["mission_id"] == "m1"
    assert events[0]["agent_id"] == "a1"


def test_resumes_seq_from_existing_file(tmp_path):
    path = tmp_path / "events.jsonl"
    w1 = EventWriter(path, mission_id="m", agent_id="a")
    w1.emit("mission.started", {})
    w1.emit("agent.thinking", {})
    w1.close()

    w2 = EventWriter(path, mission_id="m", agent_id="a")
    w2.emit("agent.thinking", {})
    w2.close()

    events = [json.loads(l) for l in path.read_text().strip().splitlines()]
    assert [e["seq"] for e in events] == [0, 1, 2]


def test_event_has_utc_timestamp(tmp_path):
    w = EventWriter(tmp_path / "events.jsonl",
                     mission_id="m", agent_id="a")
    w.emit("mission.started", {})
    w.close()
    e = json.loads((tmp_path / "events.jsonl").read_text().strip())
    assert e["ts"].endswith("Z")
