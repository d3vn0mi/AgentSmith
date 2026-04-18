"""Parses `searchsploit -j <query>` output into Vulnerability facts."""
from __future__ import annotations

import json
import re

from agent_smith.evidence.facts import Fact, Vulnerability
from agent_smith.executor.parsers.base import ToolRun


_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")


class SearchsploitParser:
    tool = "searchsploit"

    def parse(self, run: ToolRun, context: dict | None = None) -> list[Fact]:
        try:
            doc = json.loads(run.stdout)
        except json.JSONDecodeError:
            return []
        consumes = (context or {}).get("consumes") or {}
        tech_fact = consumes.get("tech")
        subject_id = tech_fact.canonical_key if tech_fact is not None else ""

        out: list[Fact] = []
        for entry in doc.get("RESULTS_EXPLOIT", []):
            title = str(entry.get("Title", "")).strip()
            if not title:
                continue
            cve_match = _CVE_RE.search(title)
            cve = cve_match.group(0) if cve_match else None
            out.append(Vulnerability.new(
                subject_id=subject_id,
                name=title,
                cve=cve,
                exploit_path=entry.get("Path"),
            ))
        return out
