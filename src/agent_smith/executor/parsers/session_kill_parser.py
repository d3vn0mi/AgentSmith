"""Parser for session_kill: emits KaliSession{dead}."""
from __future__ import annotations

import re

from agent_smith.evidence.facts import Fact, KaliSession
from agent_smith.executor.parsers.base import ToolRun


_KILLED_RE = re.compile(r"^KILLED\s+(\S+)\s*$", re.MULTILINE)


class SessionKillParser:
    tool = "session_kill"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        m = _KILLED_RE.search(run.stdout)
        if not m:
            return []
        sid = m.group(1)
        consumes = (context or {}).get("consumes") or {}
        session_fact = consumes.get("session")
        if session_fact is None:
            return []
        p = session_fact.payload
        return [KaliSession.new(
            session_id=sid,
            role=str(p.get("role") or ""),
            status="dead",
            kali_host=str(p.get("kali_host") or ""),
            metadata=dict(p.get("metadata") or {}),
        )]
