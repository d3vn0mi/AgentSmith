"""Tests for the searchsploit JSON output parser."""
from __future__ import annotations

import json
import time

from agent_smith.evidence.facts import WebTech
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.searchsploit_parser import SearchsploitParser


def _run(stdout: str) -> ToolRun:
    return ToolRun(run_id="r", tool="searchsploit",
                    command="searchsploit ...",
                    stdout=stdout, stderr="", exit_code=0,
                    duration_ms=1, started_at=time.time(),
                    finished_at=time.time())


def _ctx_with_tech(host="h", port=80, software="WordPress", version="5.8.1"):
    fact = WebTech.new(host=host, port=port,
                        software=software, version=version)
    return {"consumes": {"tech": fact}}


def test_empty_results():
    out = json.dumps({"RESULTS_EXPLOIT": []})
    facts = SearchsploitParser().parse(_run(out), _ctx_with_tech())
    assert facts == []


def test_single_exploit_no_cve():
    out = json.dumps({"RESULTS_EXPLOIT": [{
        "Title": "OpenNetAdmin 18.1.1 - Remote Code Execution",
        "Path": "php/webapps/47691.sh",
        "EDB-ID": "47691",
    }]})
    facts = SearchsploitParser().parse(_run(out), _ctx_with_tech())
    assert len(facts) == 1
    f = facts[0]
    assert f.type == "Vulnerability"
    assert f.payload["name"] == "OpenNetAdmin 18.1.1 - Remote Code Execution"
    assert f.payload["cve"] is None
    assert f.payload["exploit_path"] == "php/webapps/47691.sh"
    assert f.payload["subject_id"] == "tech:h:80:wordpress"


def test_multiple_with_cve_in_title():
    out = json.dumps({"RESULTS_EXPLOIT": [
        {"Title": "Apache Struts 2.3.5 RCE (CVE-2017-5638)",
         "Path": "linux/remote/41570.py"},
        {"Title": "WordPress Plugin X < 1.2 - SQLi", "Path": "php/webapps/x.py"},
    ]})
    facts = SearchsploitParser().parse(_run(out), _ctx_with_tech())
    assert len(facts) == 2
    cves = {f.payload["cve"] for f in facts}
    assert cves == {"CVE-2017-5638", None}


def test_missing_context_still_emits_with_empty_subject():
    out = json.dumps({"RESULTS_EXPLOIT": [
        {"Title": "x", "Path": "p"},
    ]})
    facts = SearchsploitParser().parse(_run(out), context=None)
    assert facts[0].payload["subject_id"] == ""


def test_malformed_json_returns_empty():
    facts = SearchsploitParser().parse(_run("nope"), _ctx_with_tech())
    assert facts == []
