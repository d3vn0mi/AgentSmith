"""Tests for the whatweb JSON output parser."""
from __future__ import annotations

import json
import time

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.whatweb_parser import WhatwebParser


def _run(stdout: str) -> ToolRun:
    return ToolRun(run_id="r", tool="whatweb", command="whatweb ...",
                    stdout=stdout, stderr="", exit_code=0,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def test_no_detections():
    out = json.dumps({"target": "http://10.0.0.1/", "plugins": {}})
    facts = WhatwebParser().parse(_run(out))
    assert facts == []


def test_single_plugin_with_version():
    out = json.dumps({
        "target": "http://10.0.0.1/",
        "plugins": {"WordPress": [{"version": ["5.8.1"]}]},
    })
    facts = WhatwebParser().parse(_run(out))
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "WebTech"
    assert f.payload["software"] == "WordPress"
    assert f.payload["version"] == "5.8.1"
    assert f.payload["host"] == "10.0.0.1"
    assert f.payload["port"] == 80
    assert f.canonical_key == "tech:10.0.0.1:80:wordpress"


def test_multiple_plugins_string_field_parsed():
    out = json.dumps({
        "target": "http://10.0.0.1:8080/",
        "plugins": {
            "WordPress": [{"version": ["5.8.1"]}],
            "HTTPServer": [{"string": ["nginx/1.24.0"]}],
            "PHP":       [{"version": ["7.4.3"]}],
        },
    })
    facts = WhatwebParser().parse(_run(out))
    by_software = {f.payload["software"]: f for f in facts}
    assert set(by_software) == {"WordPress", "HTTPServer", "PHP"}
    assert by_software["WordPress"].payload["version"] == "5.8.1"
    assert by_software["HTTPServer"].payload["version"] == "1.24.0"
    assert by_software["PHP"].payload["port"] == 8080


def test_malformed_input_returns_empty():
    facts = WhatwebParser().parse(_run("not json at all"))
    assert facts == []
