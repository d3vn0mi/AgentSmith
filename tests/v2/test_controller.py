"""Tests for MissionController: ties everything together for a single mission."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.types import Event, EventType
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import CommandResult


_NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
      <port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port>
    </ports>
  </host>
</nmaprun>
"""


@dataclass
class FakeSSH:
    script: dict[str, str] = field(default_factory=dict)

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        for keyword, stdout in self.script.items():
            if keyword in cmd:
                return CommandResult(command=cmd, stdout=stdout, stderr="", exit_code=0)
        return CommandResult(command=cmd, stdout="", stderr="no script match", exit_code=1)


def _builder(spec, args):
    if spec.tool == "nmap":
        return f"nmap -sV -oX - {args['target']}"
    if spec.tool == "true":
        return "true"
    return spec.tool


@pytest.fixture
def minimal_playbook_path(tmp_path: Path) -> Path:
    path = tmp_path / "p.yaml"
    path.write_text("""
name: phase1-smoke
version: "1.0"
root_tasks:
  - port_scan:
      target: "203.0.113.10"
task_types:
  port_scan:
    consumes: {}
    produces: [Host, OpenPort]
    tool: nmap
    args_template:
      target: "{target}"
    parser: nmap
  web_probe:
    consumes:
      host: Host
      port: "OpenPort{service: http|https}"
    produces: []
    tool: "true"
    args_template:
      url: "http://{host.ip}:{port.number}"
expansions:
  - id: http-probe
    on_fact: "OpenPort{service: http|https}"
    spawn: [web_probe]
terminations: [scope_exhausted]
""")
    return path


@pytest.mark.asyncio
async def test_mission_runs_root_then_expands(minimal_playbook_path, tmp_path: Path):
    ssh = FakeSSH(script={"nmap": _NMAP_XML, "true": ""})
    bus = EventBus()
    events: list[Event] = []

    async def collect(e: Event) -> None:
        events.append(e)

    bus.subscribe(collect)
    pb = load_playbook(minimal_playbook_path)

    controller = MissionController(
        mission_id="m1",
        playbook=pb,
        ssh=ssh,
        run_dir=tmp_path / "run",
        bus=bus,
        command_builder=_builder,
    )
    await controller.run()

    types = [e.event_type for e in events]
    assert EventType.MISSION_STARTED in types
    assert EventType.TASK_COMPLETE in types
    assert EventType.EXPANSION_FIRED in types
    probe_events = [
        e for e in events
        if e.event_type == EventType.TASK_RUNNING
        and e.payload.get("task_type") == "web_probe"
    ]
    assert len(probe_events) == 1  # only port 80 is http; ssh doesn't match


@pytest.mark.asyncio
async def test_mission_emits_completion_event(minimal_playbook_path, tmp_path: Path):
    ssh = FakeSSH(script={"nmap": _NMAP_XML, "true": ""})
    bus = EventBus()
    seen: list[Event] = []

    async def collect(e: Event) -> None:
        seen.append(e)

    bus.subscribe(collect, event_type=EventType.MISSION_COMPLETE)
    pb = load_playbook(minimal_playbook_path)
    controller = MissionController(
        mission_id="m1", playbook=pb, ssh=ssh, run_dir=tmp_path / "run",
        bus=bus, command_builder=_builder,
    )
    await controller.run()
    assert len(seen) == 1
