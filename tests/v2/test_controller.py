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


@pytest.mark.asyncio
async def test_fact_superseded_event_emitted_on_material_change(tmp_path: Path):
    """The controller must emit FACT_SUPERSEDED (not FACT_UPDATED) when the
    evidence store signals that a material payload change caused a supersede.
    Driven end-to-end by running two missions back-to-back against the same
    evidence store, forcing a re-observation of an OpenPort with new version info.

    Since MissionController owns its own EvidenceStore, we cannot share state
    across runs. Instead, we use a playbook with two root scans of the same
    host: the first nmap response has a port WITHOUT a version, the second
    WITH a version. The second observation materially differs and must emit
    FACT_SUPERSEDED.
    """
    nmap_no_version = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/><address addr="203.0.113.10" addrtype="ipv4"/><ports>
<port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
</ports></host></nmaprun>"""
    nmap_with_version = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/><address addr="203.0.113.10" addrtype="ipv4"/><ports>
<port protocol="tcp" portid="22"><state state="open"/><service name="ssh" product="OpenSSH" version="8.9"/></port>
</ports></host></nmaprun>"""

    @dataclass
    class SequencedSSH:
        """Returns nmap_no_version on the first call, nmap_with_version on subsequent calls."""
        call_count: int = 0

        async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
            self.call_count += 1
            stdout = nmap_no_version if self.call_count == 1 else nmap_with_version
            return CommandResult(command=cmd, stdout=stdout, stderr="", exit_code=0)

    path = tmp_path / "p.yaml"
    path.write_text("""
name: rescan
version: "1.0"
root_tasks:
  - port_scan:
      target: "203.0.113.10"
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
expansions: []
terminations: [scope_exhausted]
""")
    pb = load_playbook(path)
    bus = EventBus()
    events: list[Event] = []

    async def collect(e: Event) -> None:
        events.append(e)

    bus.subscribe(collect)
    controller = MissionController(
        mission_id="m1",
        playbook=pb,
        ssh=SequencedSSH(),
        run_dir=tmp_path / "run",
        bus=bus,
        command_builder=_builder,
    )
    await controller.run()

    # Expect exactly one FACT_SUPERSEDED (the second OpenPort observation with version)
    superseded = [e for e in events if e.event_type == EventType.FACT_SUPERSEDED]
    assert len(superseded) == 1, f"expected exactly 1 FACT_SUPERSEDED, got {len(superseded)}. types: {[e.event_type for e in events]}"
    assert superseded[0].payload["type"] == "OpenPort"
    assert superseded[0].payload["key"] == "port:203.0.113.10:tcp:22"


@pytest.mark.asyncio
async def test_task_failure_emits_paired_tool_run_complete(tmp_path: Path):
    """If the executor raises, TOOL_RUN_STARTED must still be followed by
    a closing TOOL_RUN_COMPLETE with failed=True."""
    from dataclasses import dataclass, field

    @dataclass
    class BrokenSSH:
        async def run_command(self, cmd: str, timeout: int = 60):
            raise RuntimeError("ssh blew up")

    path = tmp_path / "p.yaml"
    path.write_text("""
name: failtest
version: "1.0"
root_tasks:
  - port_scan:
      target: "1.2.3.4"
task_types:
  port_scan:
    consumes: {}
    produces: [Host]
    tool: nmap
    args_template:
      target: "{target}"
    parser: nmap
expansions: []
terminations: [scope_exhausted]
""")
    pb = load_playbook(path)
    bus = EventBus()
    events: list[Event] = []

    async def collect(e: Event) -> None:
        events.append(e)

    bus.subscribe(collect)
    controller = MissionController(
        mission_id="m1", playbook=pb, ssh=BrokenSSH(), run_dir=tmp_path / "run",
        bus=bus, command_builder=_builder,
    )
    await controller.run()

    types = [e.event_type for e in events]
    started_count = types.count(EventType.TOOL_RUN_STARTED)
    complete_count = types.count(EventType.TOOL_RUN_COMPLETE)
    assert started_count >= 1
    assert complete_count == started_count, f"unpaired tool-run events: {types}"
    assert EventType.TASK_FAILED in types


@pytest.mark.asyncio
async def test_root_tasks_emit_created_and_ready_events(minimal_playbook_path, tmp_path: Path):
    """Root tasks must emit TASK_CREATED and TASK_READY, matching the
    pattern used for spawned tasks. This is what lets downstream consumers
    reconstruct the graph state from the event stream alone."""
    ssh = FakeSSH(script={"nmap": _NMAP_XML, "true": ""})
    bus = EventBus()
    events: list[Event] = []

    async def collect(e: Event) -> None:
        events.append(e)

    bus.subscribe(collect)
    pb = load_playbook(minimal_playbook_path)
    controller = MissionController(
        mission_id="m1", playbook=pb, ssh=ssh, run_dir=tmp_path / "run",
        bus=bus, command_builder=_builder,
    )
    await controller.run()

    # The single root task_type is port_scan; it should have CREATED+READY before RUNNING
    created = [e for e in events if e.event_type == EventType.TASK_CREATED and e.payload.get("task_type") == "port_scan"]
    ready = [e for e in events if e.event_type == EventType.TASK_READY and e.task_id and e.task_id.startswith("port_scan#")]
    running = [e for e in events if e.event_type == EventType.TASK_RUNNING and e.payload.get("task_type") == "port_scan"]
    assert len(created) == 1
    assert len(ready) == 1
    assert len(running) == 1
    # Ordering: CREATED before READY before RUNNING
    created_idx = events.index(created[0])
    ready_idx = events.index(ready[0])
    running_idx = events.index(running[0])
    assert created_idx < ready_idx < running_idx
