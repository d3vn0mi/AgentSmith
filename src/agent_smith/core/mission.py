"""Mission state machine and phase tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Phase(str, Enum):
    RECON = "recon"
    ENUMERATION = "enumeration"
    EXPLOITATION = "exploitation"
    PRIVESC = "privesc"
    POST_EXPLOIT = "post_exploit"
    COMPLETE = "complete"


PHASE_ORDER = [
    Phase.RECON,
    Phase.ENUMERATION,
    Phase.EXPLOITATION,
    Phase.PRIVESC,
    Phase.POST_EXPLOIT,
    Phase.COMPLETE,
]

PHASE_OBJECTIVES = {
    Phase.RECON: "Discover open ports and services on the target. Run nmap scans to identify the attack surface.",
    Phase.ENUMERATION: "Deep-dive into discovered services. Enumerate web directories, check for default credentials, identify versions and potential vulnerabilities.",
    Phase.EXPLOITATION: "Exploit identified vulnerabilities to gain initial access. Get a shell as a regular user and find user.txt flag.",
    Phase.PRIVESC: "Escalate privileges from regular user to root. Check SUID binaries, sudo permissions, cron jobs, kernel exploits.",
    Phase.POST_EXPLOIT: "Capture the root.txt flag and document the full attack path.",
    Phase.COMPLETE: "Mission complete. Both flags captured.",
}


@dataclass
class HistoryEntry:
    """A single step in the agent's history."""
    iteration: int
    phase: str
    thinking: str
    tool_name: str
    tool_args: dict[str, Any]
    output: str
    timestamp: float = field(default_factory=time.time)


class Mission:
    """Tracks the state of the penetration testing mission."""

    def __init__(self, target_ip: str, max_iterations: int = 200) -> None:
        self.target_ip = target_ip
        self.max_iterations = max_iterations
        self.current_phase: Phase = Phase.RECON
        self.iteration: int = 0
        self.history: list[HistoryEntry] = []
        self.start_time: float = time.time()
        self.paused: bool = False
        self._phase_start_times: dict[Phase, float] = {Phase.RECON: time.time()}

    def advance_phase(self) -> Phase:
        """Move to the next phase."""
        current_idx = PHASE_ORDER.index(self.current_phase)
        if current_idx < len(PHASE_ORDER) - 1:
            self.current_phase = PHASE_ORDER[current_idx + 1]
            self._phase_start_times[self.current_phase] = time.time()
        return self.current_phase

    def set_phase(self, phase: Phase) -> None:
        """Explicitly set the current phase (e.g., from LLM reasoning)."""
        self.current_phase = phase
        if phase not in self._phase_start_times:
            self._phase_start_times[phase] = time.time()

    def add_history(self, entry: HistoryEntry) -> None:
        self.history.append(entry)
        self.iteration += 1

    def recent_history(self, n: int = 20) -> list[HistoryEntry]:
        """Get the last N history entries."""
        return self.history[-n:]

    def is_complete(self) -> bool:
        return self.current_phase == Phase.COMPLETE

    def is_over_limit(self) -> bool:
        return self.iteration >= self.max_iterations

    @property
    def current_objective(self) -> str:
        return PHASE_OBJECTIVES.get(self.current_phase, "")

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def phase_elapsed_seconds(self) -> float:
        start = self._phase_start_times.get(self.current_phase, self.start_time)
        return time.time() - start

    def to_dict(self) -> dict[str, Any]:
        """Serialize mission state for API responses."""
        return {
            "target_ip": self.target_ip,
            "current_phase": self.current_phase.value,
            "objective": self.current_objective,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "paused": self.paused,
            "history_count": len(self.history),
        }
