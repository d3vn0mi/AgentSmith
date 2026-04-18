"""Event persistence: appends every event to events.jsonl in the mission run dir."""
from __future__ import annotations

import asyncio
from pathlib import Path

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.types import Event


class JsonlEventPersister:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self._file_path = run_dir / "events.jsonl"
        self._lock = asyncio.Lock()
        self._run_dir_ready = False

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(self._on_event, event_type=None)

    async def _on_event(self, event: Event) -> None:
        async with self._lock:
            if not self._run_dir_ready:
                self.run_dir.mkdir(parents=True, exist_ok=True)
                self._run_dir_ready = True
            with self._file_path.open("a", encoding="utf-8") as fh:
                fh.write(event.model_dump_json() + "\n")

    async def flush(self) -> None:
        return None
