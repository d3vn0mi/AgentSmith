"""Tests for the nmap XML parser."""
from __future__ import annotations

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.nmap_parser import NmapXmlParser


_XML_SIMPLE = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <hostnames><hostname name="target.example"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.25.3"/>
      </port>
      <port protocol="tcp" portid="3389">
        <state state="filtered"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


def _run(stdout: str) -> ToolRun:
    return ToolRun(
        run_id="r1",
        tool="nmap",
        command="nmap -sV -oX - 203.0.113.10",
        stdout=stdout,
        stderr="",
        exit_code=0,
        duration_ms=1000,
        started_at=0.0,
        finished_at=1.0,
    )


def test_emits_host_and_open_ports():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    kinds = [f.type for f in facts]
    assert kinds.count("Host") == 1
    assert kinds.count("OpenPort") == 2
    host = next(f for f in facts if f.type == "Host")
    assert host.payload["ip"] == "203.0.113.10"
    assert host.payload["hostname"] == "target.example"
    assert host.payload["alive"] is True

    ports = {f.payload["number"]: f for f in facts if f.type == "OpenPort"}
    assert set(ports) == {22, 80}
    assert ports[22].payload["service"] == "ssh"
    assert ports[22].payload["version"] == "OpenSSH 8.9"
    assert ports[80].payload["service"] == "http"


def test_skips_non_open_ports():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    assert all(f.payload.get("number") != 3389 for f in facts if f.type == "OpenPort")


def test_marks_provenance_on_emitted_facts():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    for f in facts:
        assert len(f.provenance) == 1
        prov = f.provenance[0]
        assert prov.parser == "nmap"
        assert prov.tool_run_id == "r1"


def test_handles_garbage_input_gracefully():
    facts = NmapXmlParser().parse(_run("not xml at all"))
    assert facts == []
