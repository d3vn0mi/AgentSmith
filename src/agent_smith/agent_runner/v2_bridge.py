"""Bridges v2 engine's event_stream.bus events to the mission's on-disk
observability surfaces (events.jsonl via EventWriter + evidence.json).
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.event_stream.bus import EventBus as V2Bus
from agent_smith.event_stream.types import Event, EventType


_TRANSLATE = {
    EventType.TOOL_RUN_STARTED:  "tool.run_started",
    EventType.TOOL_RUN_COMPLETE: "tool.run_finished",
    EventType.FACT_EMITTED:      "evidence.added",
    EventType.MISSION_HALTED:    "mission.stopped",
    # TASK_FAILED is bridged as a failed tool.run_finished (see _handle)
}


class V2EventBridge:
    def __init__(self, bus: V2Bus, writer: EventWriter, mission_dir: Path) -> None:
        self._bus = bus
        self._writer = writer
        self._mission_dir = Path(mission_dir)
        self._mission_dir.mkdir(parents=True, exist_ok=True)
        self._evidence_snapshot: dict[str, list[dict]] = {}
        self._started = False

    async def start(self) -> None:
        self._bus.subscribe(self._handle)
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def _handle(self, event: Event) -> None:
        if not self._started:
            return
        try:
            et = event.event_type
            if et == EventType.FACT_EMITTED:
                self._snapshot_fact(event.payload)
                self._writer.emit("evidence.added", {
                    "category": str(event.payload.get("type", "")).lower(),
                    "item": event.payload,
                })
                return
            if et == EventType.TASK_FAILED:
                self._writer.emit("tool.run_finished", {
                    "tool": event.payload.get("tool"),
                    "exit_code": event.payload.get("exit_code", 1),
                    "duration_ms": event.payload.get("duration_ms", 0),
                    "stdout_preview": event.payload.get("stdout_preview", ""),
                    "run_id": event.payload.get("run_id"),
                    "failed": True,
                })
                return
            mapped = _TRANSLATE.get(et)
            if mapped is None:
                return
            self._writer.emit(mapped, dict(event.payload))
        except Exception:
            return

    def _snapshot_fact(self, payload: dict) -> None:
        ftype = payload.get("type")
        if not ftype:
            return
        bucket = self._evidence_snapshot.setdefault(ftype, [])
        key = payload.get("canonical_key")
        if key is not None:
            bucket = [e for e in bucket if e.get("canonical_key") != key]
        bucket.append(payload)
        self._evidence_snapshot[ftype] = bucket
        (self._mission_dir / "evidence.json").write_text(
            json.dumps(self._evidence_snapshot, indent=2))
