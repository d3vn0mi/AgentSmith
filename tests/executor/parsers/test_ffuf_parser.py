"""Tests for the ffuf JSON output parser."""
from __future__ import annotations

import json
import time

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.ffuf_parser import FfufParser


def _run(stdout: str) -> ToolRun:
    return ToolRun(run_id="r", tool="ffuf", command="ffuf ...",
                    stdout=stdout, stderr="", exit_code=0,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def test_empty_results():
    out = json.dumps({"results": []})
    facts = FfufParser().parse(_run(out))
    assert facts == []


def test_single_hit():
    out = json.dumps({"results": [
        {"url": "http://10.0.0.1/admin", "status": 301, "length": 178},
    ]})
    facts = FfufParser().parse(_run(out))
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "DirPath"
    assert f.canonical_key == "dir:http://10.0.0.1/admin"
    assert f.payload["status"] == 301
    assert f.payload["size"] == 178
    assert f.payload["host"] == "10.0.0.1"
    assert f.payload["port"] == 80


def test_multiple_hits_with_https_and_custom_port():
    out = json.dumps({"results": [
        {"url": "http://10.0.0.1/a", "status": 200, "length": 1},
        {"url": "https://10.0.0.1:8443/b", "status": 200, "length": 2},
    ]})
    facts = FfufParser().parse(_run(out))
    assert [f.payload["port"] for f in facts] == [80, 8443]


def test_malformed_json_returns_empty():
    facts = FfufParser().parse(_run("not json"))
    assert facts == []
