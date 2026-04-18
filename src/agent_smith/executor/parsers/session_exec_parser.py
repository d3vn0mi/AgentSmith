"""Parser for session_exec: liveness supersede only; stdout passes through."""
from __future__ import annotations

import re

from agent_smith.evidence.facts import Fact, KaliSession, Shell
from agent_smith.executor.parsers.base import ToolRun


_DEAD_RE = re.compile(r"^DEAD\s+(\S+)\s*$", re.MULTILINE)


class SessionExecParser:
    tool = "session_exec"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        m = _DEAD_RE.search(run.stderr or "")
        if not m:
            return []
        dead_sid = m.group(1)
        consumes = (context or {}).get("consumes") or {}
        session_fact = consumes.get("session")
        shell_fact = consumes.get("shell")

        out: list[Fact] = []
        if session_fact is not None:
            p = session_fact.payload
            out.append(KaliSession.new(
                session_id=dead_sid,
                role=str(p.get("role") or ""),
                status="dead",
                kali_host=str(p.get("kali_host") or ""),
                metadata=dict(p.get("metadata") or {}),
            ))
        if shell_fact is not None:
            p = shell_fact.payload
            out.append(Shell.new(
                session_id=dead_sid,
                target_host=str(p.get("target_host") or ""),
                listener_port=int(p.get("listener_port") or 0),
                callback_ip=str(p.get("callback_ip") or ""),
                target_user=p.get("target_user"),
                interactive=bool(p.get("interactive")),
                status="dead",
            ))
        return out
