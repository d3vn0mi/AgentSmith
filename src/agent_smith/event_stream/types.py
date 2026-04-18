"""Typed events produced by the v2 engine."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETE = "mission_complete"
    MISSION_HALTED = "mission_halted"
    SCENARIO_LOADED = "scenario_loaded"
    TASK_CREATED = "task_created"
    TASK_READY = "task_ready"
    TASK_RUNNING = "task_running"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    EXPANSION_FIRED = "expansion_fired"
    TOOL_RUN_STARTED = "tool_run_started"
    TOOL_RUN_COMPLETE = "tool_run_complete"
    TOOL_RUN_OUTPUT = "tool_run_output"
    FACT_EMITTED = "fact_emitted"
    FACT_UPDATED = "fact_updated"
    FACT_SUPERSEDED = "fact_superseded"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    mission_id: str
    task_id: str | None = None
    timestamp: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1

    model_config = {"extra": "forbid"}
