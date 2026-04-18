"""Parses session_start output into a KaliSession fact."""
from __future__ import annotations

import re

from agent_smith.evidence.facts import Fact, KaliSession
from agent_smith.executor.parsers.base import ToolRun


_OK_RE = re.compile(r"^OK\s+(\S+)\s*$", re.MULTILINE)


class KaliSessionParser:
    tool = "kali_session"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        m = _OK_RE.search(run.stdout)
        if not m:
            return []
        session_id = m.group(1)
        args = (context or {}).get("args") or {}
        return [KaliSession.new(
            session_id=session_id,
            role=str(args.get("role") or ""),
            status="starting",
            kali_host=str(args.get("kali_host") or ""),
        )]
