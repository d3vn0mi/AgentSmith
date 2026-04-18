"""Parses ffuf `-of json` output into DirPath facts."""
from __future__ import annotations

import json
from urllib.parse import urlsplit

from agent_smith.evidence.facts import DirPath, Fact
from agent_smith.executor.parsers.base import ToolRun


def _host_port(url: str) -> tuple[str, int]:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port is not None:
        return host, parts.port
    if parts.scheme == "https":
        return host, 443
    return host, 80


class FfufParser:
    tool = "ffuf"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        try:
            doc = json.loads(run.stdout)
        except json.JSONDecodeError:
            return []
        out: list[Fact] = []
        for entry in doc.get("results", []):
            url = entry.get("url")
            if not url:
                continue
            host, port = _host_port(url)
            out.append(DirPath.new(
                host=host, port=port, url=url,
                status=int(entry.get("status", 0)),
                size=entry.get("length"),
            ))
        return out
