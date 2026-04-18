"""Parser protocol and shared input types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_smith.evidence.facts import Fact


@dataclass
class ToolRun:
    run_id: str
    tool: str
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    started_at: float
    finished_at: float
    timed_out: bool = False
    artifact_paths: list[str] = field(default_factory=list)


class Parser(Protocol):
    tool: str

    def parse(self, run: ToolRun) -> list[Fact]:
        ...
