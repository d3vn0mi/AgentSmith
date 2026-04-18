"""Tests for the V2EventBridge."""
from __future__ import annotations

import asyncio
import json

import pytest

from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.agent_runner.v2_bridge import V2EventBridge
from agent_smith.event_stream.bus import EventBus as V2Bus
from agent_smith.event_stream.types import Event, EventType


def _read_events(path):
    return [json.loads(l) for l in path.read_text().strip().splitlines() if l]


@pytest.fixture
def setup(tmp_path):
    bus = V2Bus()
    writer = EventWriter(tmp_path / "events.jsonl",
                          mission_id="m", agent_id="a")
    bridge = V2EventBridge(bus, writer, tmp_path)
    return bus, writer, bridge, tmp_path


@pytest.mark.asyncio
async def test_tool_run_started_maps(setup):
    bus, writer, bridge, tmp = setup
    await bridge.start()
    await bus.publish(Event(event_type=EventType.TOOL_RUN_STARTED,
                             mission_id="m", task_id="t1",
                             payload={"tool": "nmap",
                                      "command": "nmap -sV 10.0.0.1",
                                      "run_id": "r1"}))
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()
    events = _read_events(tmp / "events.jsonl")
    assert events[0]["type"] == "tool.run_started"
    assert events[0]["data"]["tool"] == "nmap"
    assert events[0]["data"]["run_id"] == "r1"


@pytest.mark.asyncio
async def test_tool_run_complete_maps(setup):
    bus, writer, bridge, tmp = setup
    await bridge.start()
    await bus.publish(Event(event_type=EventType.TOOL_RUN_COMPLETE,
                             mission_id="m", task_id="t1",
                             payload={"tool": "nmap", "exit_code": 0,
                                      "duration_ms": 123,
                                      "stdout_preview": "ok",
                                      "run_id": "r1"}))
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()
    events = _read_events(tmp / "events.jsonl")
    assert events[0]["type"] == "tool.run_finished"
    assert events[0]["data"]["exit_code"] == 0
    assert events[0]["data"]["duration_ms"] == 123


@pytest.mark.asyncio
async def test_fact_emitted_maps_and_snapshots(setup):
    bus, writer, bridge, tmp = setup
    await bridge.start()
    await bus.publish(Event(event_type=EventType.FACT_EMITTED,
                             mission_id="m",
                             payload={"type": "WebTech",
                                      "canonical_key": "tech:h:80:nginx",
                                      "payload": {"host": "h", "port": 80,
                                                  "software": "nginx"}}))
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    events = _read_events(tmp / "events.jsonl")
    assert events[0]["type"] == "evidence.added"
    assert events[0]["data"]["category"] == "webtech"
    assert events[0]["data"]["item"]["canonical_key"] == "tech:h:80:nginx"

    snap = json.loads((tmp / "evidence.json").read_text())
    assert "WebTech" in snap
    assert snap["WebTech"][0]["canonical_key"] == "tech:h:80:nginx"


@pytest.mark.asyncio
async def test_drops_noisy_events(setup):
    bus, writer, bridge, tmp = setup
    await bridge.start()
    for et in (EventType.TASK_CREATED, EventType.TASK_READY,
                EventType.TASK_RUNNING, EventType.TASK_SKIPPED,
                EventType.FACT_SUPERSEDED, EventType.FACT_UPDATED,
                EventType.EXPANSION_FIRED, EventType.SCENARIO_LOADED,
                EventType.TOOL_RUN_OUTPUT):
        await bus.publish(Event(event_type=et, mission_id="m", payload={}))
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()
    raw = (tmp / "events.jsonl").read_text().strip()
    assert raw == ""
