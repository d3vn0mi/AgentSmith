"""Tests for typed events."""
from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from agent_smith.event_stream.types import Event, EventType


def test_event_types_cover_phase1_lifecycle():
    required = {
        "mission_started",
        "mission_complete",
        "mission_halted",
        "scenario_loaded",
        "task_created",
        "task_ready",
        "task_running",
        "task_complete",
        "task_failed",
        "expansion_fired",
        "tool_run_started",
        "tool_run_complete",
        "fact_emitted",
        "fact_updated",
    }
    assert required.issubset({e.value for e in EventType})


def test_event_has_stable_id_and_timestamp():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.event_id  # uuid populated
    assert e.timestamp <= time.time() + 1
    assert e.schema_version == 1


def test_event_task_id_is_optional():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.task_id is None


def test_event_rejects_unknown_type_string():
    with pytest.raises(ValidationError):
        Event.model_validate({"event_type": "not_a_real_type", "mission_id": "m1"})


def test_event_round_trips_through_json():
    original = Event(
        event_type=EventType.TASK_RUNNING,
        mission_id="m1",
        task_id="t1",
        payload={"cmd": "nmap -sV 1.2.3.4"},
    )
    wire = original.model_dump_json()
    restored = Event.model_validate_json(wire)
    assert restored.event_type == original.event_type
    assert restored.mission_id == "m1"
    assert restored.task_id == "t1"
    assert restored.payload["cmd"] == "nmap -sV 1.2.3.4"
    assert restored.event_id == original.event_id


def test_event_payload_defaults_to_empty_dict():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.payload == {}
