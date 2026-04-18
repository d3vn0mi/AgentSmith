"""End-to-end integration: htb_easy_recon against a mocked SSH."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook


NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="10.0.0.1" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.24.0"/>
      </port>
    </ports>
  </host>
</nmaprun>"""

FFUF_JSON = json.dumps({
    "results": [
        {"url": "http://10.0.0.1/admin", "status": 301, "length": 178},
        {"url": "http://10.0.0.1/robots.txt", "status": 200, "length": 42},
    ]
})

WHATWEB_JSON = json.dumps({
    "target": "http://10.0.0.1/",
    "plugins": {
        "HTTPServer": [{"string": ["nginx/1.24.0"]}],
        "WordPress":   [{"version": ["5.8.1"]}],
    },
})

SEARCHSPLOIT_JSON = json.dumps({
    "RESULTS_EXPLOIT": [
        {"Title": "WordPress 5.8.1 RCE (CVE-2023-99999)",
         "Path": "php/webapps/99999.py"},
    ]
})


class FakeSsh:
    """Mimics the SSH protocol used by ShellRunner.

    ShellRunner.run() accesses result.stdout, result.stderr,
    result.exit_code, and result.timed_out on the object returned by
    ssh.run_command().
    """
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses

    async def run_command(self, cmd: str, timeout: int = 60):
        class R:
            stdout = ""
            stderr = ""
            exit_code = 0
            timed_out = False

        r = R()
        for key, out in self.responses.items():
            if key in cmd:
                r.stdout = out
                break
        return r


@pytest.mark.asyncio
async def test_htb_easy_recon_emits_dirpath_webtech_vulnerability(tmp_path):
    responses = {
        "nmap ": NMAP_XML,
        "ffuf ": FFUF_JSON,
        "whatweb ": WHATWEB_JSON,
        "searchsploit ": SEARCHSPLOIT_JSON,
    }
    ssh = FakeSsh(responses)
    pb = load_playbook(
        Path(__file__).parent.parent.parent.parent
        / "src/agent_smith/playbooks/htb_easy_recon.yaml"
    )

    # Pre-substitute ${TARGET} on root tasks' args — the controller does not do it.
    for root in pb.root_tasks:
        for k, v in list(root.args.items()):
            if isinstance(v, str):
                root.args[k] = v.replace("${TARGET}", "10.0.0.1")

    bus = EventBus()
    controller = MissionController(
        mission_id="m",
        playbook=pb,
        ssh=ssh,
        run_dir=tmp_path,
        bus=bus,
    )
    await controller.run()

    # EvidenceStore.all() returns all non-superseded facts.
    facts = controller.evidence.all()
    types = sorted({f.type for f in facts})

    assert "Host" in types
    assert "OpenPort" in types
    assert "DirPath" in types
    assert "WebTech" in types
    assert "Vulnerability" in types

    vulns = [f for f in facts if f.type == "Vulnerability"]
    webtechs = [f for f in facts if f.type == "WebTech"]
    wp_keys = {
        f.canonical_key for f in webtechs
        if f.payload["software"].lower() == "wordpress"
    }
    assert any(v.payload["subject_id"] in wp_keys for v in vulns)
