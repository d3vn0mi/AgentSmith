"""Bridges the core agent's EventBus to the mission's on-disk observability
surfaces: events.jsonl (via EventWriter), evidence.json, history.jsonl.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.events import Event, EventBus


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z")


class EventBridge:
    """Subscribes to an EventBus and drives the mission's observability files."""

    def __init__(self, bus: EventBus, writer: EventWriter, mission_dir: Path) -> None:
        self._bus = bus
        self._writer = writer
        self._mission_dir = Path(mission_dir)
        self._mission_dir.mkdir(parents=True, exist_ok=True)
        self._queue: Optional[asyncio.Queue[Event]] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._queue = self._bus.subscribe()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._queue is not None:
            self._bus.unsubscribe(self._queue)
            self._queue = None

    async def _loop(self) -> None:
        assert self._queue is not None
        while True:
            event = await self._queue.get()
            try:
                self._handle(event)
            except Exception:
                # Never let a translation error take down the bridge.
                pass

    # ---- Translation ----

    def _handle(self, event: Event) -> None:
        t = event.type
        d = event.data or {}
        if t == "thought":
            self._writer.emit("agent.thinking", {
                "reasoning": str(d.get("thinking", ""))[:2000],
                "iteration": d.get("iteration"),
            })
        elif t == "command_executing":
            self._writer.emit("tool.run_started", {
                "tool": d.get("tool"),
                "args_preview": str(d.get("args", ""))[:200],
                "iteration": d.get("iteration"),
            })
        elif t == "command_executed":
            success = bool(d.get("success"))
            self._writer.emit("tool.run_finished", {
                "tool": d.get("tool"),
                "exit_code": 0 if success else 1,
                "stdout_preview": str(d.get("output", ""))[:500],
                "success": success,
                "iteration": d.get("iteration"),
            })
            self._append_history(d)
        elif t == "flag_captured":
            self._writer.emit("evidence.added", {
                "category": "flags",
                "item": {"type": d.get("type"), "value": d.get("value")},
            })
        elif t == "evidence_updated":
            self._write_evidence_snapshot(d)
        elif t == "phase_changed":
            self._writer.emit("phase.entered", {
                "to": d.get("phase"),
                "reason": d.get("reason"),
            })
        # mission_started / mission_complete / mission_timeout / error / thinking
        # are intentionally dropped — runner handles mission lifecycle; `thinking`
        # is duplicated by `thought`.

    def _write_evidence_snapshot(self, evidence: dict) -> None:
        path = self._mission_dir / "evidence.json"
        path.write_text(json.dumps(evidence, indent=2))

    def _append_history(self, d: dict) -> None:
        path = self._mission_dir / "history.jsonl"
        row = {
            "ts": _utc_ts(),
            "iteration": d.get("iteration"),
            "tool": d.get("tool"),
            "command": str(d.get("args", ""))[:2000],
            "exit_code": 0 if d.get("success") else 1,
            "stdout_preview": str(d.get("output", ""))[:2000],
        }
        with path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
