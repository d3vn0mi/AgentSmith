"""Typed facts emitted by the evidence store.

Each fact has a stable canonical_key for dedup, a confidence score,
and append-only provenance that tracks which task/tool/parser observed it.

MVP fact types (Host, OpenPort, WebEndpoint) live in this module too;
they are added in the next task.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provenance:
    task_id: str
    tool_run_id: str
    parser: str
    timestamp: float
    snippet: str


@dataclass
class Fact:
    type: str
    payload: dict[str, Any]
    canonical_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provenance: list[Provenance] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    superseded_by: str | None = None
    confidence: float = 1.0

    def append_provenance(self, p: Provenance) -> None:
        self.provenance.append(p)
        self.last_seen_at = time.time()
