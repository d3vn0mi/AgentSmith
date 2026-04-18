"""Tests for the EventBridge."""
from __future__ import annotations

import asyncio
import json

import pytest

from agent_smith.agent_runner.bridge import EventBridge
from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.events import EventBus


@pytest.fixture
def setup(tmp_path):
    bus = EventBus()
    writer = EventWriter(tmp_path / "events.jsonl",
                          mission_id="m", agent_id="a")
    bridge = EventBridge(bus, writer, tmp_path)
    return bus, writer, bridge, tmp_path


def _read_events(path):
    return [json.loads(l) for l in path.read_text().strip().splitlines() if l]


@pytest.mark.asyncio
async def test_thought_maps_to_agent_thinking(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("thought", {"thinking": "planning an nmap scan", "iteration": 1})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()
    events = _read_events(tmp_path / "events.jsonl")
    assert events[0]["type"] == "agent.thinking"
    assert events[0]["data"]["reasoning"] == "planning an nmap scan"
    assert events[0]["data"]["iteration"] == 1


@pytest.mark.asyncio
async def test_command_executed_maps_and_appends_history(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("command_executing", {
        "tool": "nmap", "args": {"target": "10.0.0.1"}, "iteration": 2})
    await bus.emit("command_executed", {
        "tool": "nmap", "args": {"target": "10.0.0.1"},
        "output": "Starting Nmap scan...", "success": True, "iteration": 2})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    events = _read_events(tmp_path / "events.jsonl")
    types = [e["type"] for e in events]
    assert "tool.run_started" in types
    assert "tool.run_finished" in types

    history = _read_events(tmp_path / "history.jsonl")
    assert len(history) == 1
    assert history[0]["tool"] == "nmap"
    assert history[0]["exit_code"] == 0


@pytest.mark.asyncio
async def test_evidence_updated_snapshots_file(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("evidence_updated", {
        "flags": ["HTB{foo}"], "ports": [{"port": 80}],
        "credentials": [], "vulnerabilities": [], "files": []})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    evidence = json.loads((tmp_path / "evidence.json").read_text())
    assert evidence["flags"] == ["HTB{foo}"]
    # evidence_updated does NOT emit an event
    events = _read_events(tmp_path / "events.jsonl")
    assert all(e["type"] != "evidence.added" for e in events)


@pytest.mark.asyncio
async def test_flag_captured_maps_to_evidence_added(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("flag_captured", {"type": "root", "value": "HTB{root_flag}"})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    events = _read_events(tmp_path / "events.jsonl")
    assert events[0]["type"] == "evidence.added"
    assert events[0]["data"]["category"] == "flags"
    assert events[0]["data"]["item"]["value"] == "HTB{root_flag}"


@pytest.mark.asyncio
async def test_phase_changed_maps_to_phase_entered(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("phase_changed", {"phase": "enumeration"})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    events = _read_events(tmp_path / "events.jsonl")
    assert events[0]["type"] == "phase.entered"
    assert events[0]["data"]["to"] == "enumeration"


@pytest.mark.asyncio
async def test_dropped_events_not_emitted(setup):
    bus, writer, bridge, tmp_path = setup
    await bridge.start()
    await bus.emit("mission_started", {})
    await bus.emit("mission_complete", {})
    await bus.emit("mission_timeout", {})
    await bus.emit("error", {"error": "x"})
    await bus.emit("thinking", {"iteration": 1})
    await asyncio.sleep(0.05)
    await bridge.stop()
    writer.close()

    events = _read_events(tmp_path / "events.jsonl") if (tmp_path / "events.jsonl").read_text().strip() else []
    assert events == []
