"""Append-only JSONL event writer for one mission+agent."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z")


class EventWriter:
    def __init__(self, path, *, mission_id: str, agent_id: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._mission_id = mission_id
        self._agent_id = agent_id
        self._seq = self._count_existing_lines()
        self._fh = self._path.open("a", buffering=1)

    def _count_existing_lines(self) -> int:
        if not self._path.exists():
            return 0
        with self._path.open("rb") as f:
            return sum(1 for _ in f)

    def emit(self, event_type: str, data: dict[str, Any]) -> int:
        envelope = {
            "ts": _utc_ts(),
            "seq": self._seq,
            "type": event_type,
            "mission_id": self._mission_id,
            "agent_id": self._agent_id,
            "data": data,
        }
        self._fh.write(json.dumps(envelope, separators=(",", ":")) + "\n")
        self._fh.flush()
        self._seq += 1
        return envelope["seq"]

    def close(self) -> None:
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
