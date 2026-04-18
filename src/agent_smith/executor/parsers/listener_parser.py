"""Parses listener_start output into KaliSession+Shell facts."""
from __future__ import annotations

import re

from agent_smith.evidence.facts import Fact, KaliSession, Shell
from agent_smith.executor.parsers.base import ToolRun


# READY <sid> <callback_ip> <port> <user> <interactive 0|1> <target_ip>
_READY_RE = re.compile(
    r"^READY\s+(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s+([01])\s+(\S+)\s*$",
    re.MULTILINE,
)


class ListenerParser:
    tool = "listener"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        m = _READY_RE.search(run.stdout)
        if not m:
            return []
        session_id, callback_ip, port_s, user, interactive_s, target_ip = m.groups()
        args = (context or {}).get("args") or {}
        kali_host = str(args.get("kali_host") or "")
        return [
            KaliSession.new(
                session_id=session_id, role="shell",
                status="live", kali_host=kali_host,
            ),
            Shell.new(
                session_id=session_id,
                target_host=target_ip,
                listener_port=int(port_s),
                callback_ip=callback_ip,
                target_user=user,
                interactive=(interactive_s == "1"),
                status="live",
            ),
        ]
