"""Tests for JSONL event persistence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.persistence import JsonlEventPersister
from agent_smith.event_stream.types import Event, EventType


@pytest.mark.asyncio
async def test_persister_writes_event_to_jsonl(tmp_path: Path):
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=tmp_path)
    persister.attach(bus)

    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    await persister.flush()

    events_path = tmp_path / "events.jsonl"
    assert events_path.exists()
    lines = events_path.read_text().strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["event_type"] == "mission_started"
    assert obj["mission_id"] == "m1"


@pytest.mark.asyncio
async def test_persister_appends_multiple_events(tmp_path: Path):
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=tmp_path)
    persister.attach(bus)

    for i in range(3):
        await bus.publish(
            Event(event_type=EventType.TASK_RUNNING, mission_id="m1", task_id=f"t{i}")
        )
    await persister.flush()

    lines = (tmp_path / "events.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_persister_creates_run_dir_if_missing(tmp_path: Path):
    run_dir = tmp_path / "nested" / "run"
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=run_dir)
    persister.attach(bus)

    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    await persister.flush()

    assert (run_dir / "events.jsonl").exists()
