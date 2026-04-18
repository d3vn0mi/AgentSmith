"""Parses `whatweb -a 3 --log-json=-` output into WebTech facts."""
from __future__ import annotations

import json
from urllib.parse import urlsplit

from agent_smith.evidence.facts import Fact, WebTech
from agent_smith.executor.parsers.base import ToolRun


def _host_port(url: str) -> tuple[str, int]:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port is not None:
        return host, parts.port
    if parts.scheme == "https":
        return host, 443
    return host, 80


def _extract_version(entry: dict) -> str | None:
    versions = entry.get("version")
    if isinstance(versions, list) and versions:
        return str(versions[0])
    strings = entry.get("string")
    if isinstance(strings, list) and strings:
        s = str(strings[0])
        if "/" in s:
            return s.rsplit("/", 1)[-1]
        return s
    return None


class WhatwebParser:
    tool = "whatweb"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        raw = run.stdout.strip()
        if not raw:
            return []
        first_line = raw.splitlines()[0]
        try:
            doc = json.loads(first_line)
        except json.JSONDecodeError:
            return []
        target = doc.get("target") or ""
        host, port = _host_port(target)
        plugins = doc.get("plugins") or {}
        out: list[Fact] = []
        for software, entries in plugins.items():
            if not isinstance(entries, list) or not entries:
                out.append(WebTech.new(host=host, port=port,
                                         software=software))
                continue
            version = _extract_version(entries[0])
            out.append(WebTech.new(host=host, port=port,
                                     software=software, version=version))
        return out
