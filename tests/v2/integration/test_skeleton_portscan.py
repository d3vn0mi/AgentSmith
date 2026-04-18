"""End-to-end skeleton_portscan playbook run with a mocked SSH transport."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import CommandResult


_NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
      <port protocol="tcp" portid="80"><state state="open"/><service name="http" product="nginx" version="1.25"/></port>
      <port protocol="tcp" portid="443"><state state="open"/><service name="https"/></port>
    </ports>
  </host>
</nmaprun>
"""


@dataclass
class FakeSSH:
    last_commands: list[str] = field(default_factory=list)

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_commands.append(cmd)
        if "nmap" in cmd:
            return CommandResult(command=cmd, stdout=_NMAP_XML, stderr="", exit_code=0)
        if "curl" in cmd:
            return CommandResult(command=cmd, stdout="<html>ok</html>", stderr="", exit_code=0)
        return CommandResult(command=cmd, stdout="", stderr="unknown cmd", exit_code=1)


@pytest.mark.asyncio
async def test_skeleton_mission_runs_and_events_are_persisted(tmp_path: Path):
    playbook_path = Path("src/agent_smith/playbooks/skeleton_portscan.yaml")
    raw = playbook_path.read_text().replace("${TARGET}", "203.0.113.10")
    staged = tmp_path / "skeleton_portscan.yaml"
    staged.write_text(raw)
    pb = load_playbook(staged)

    def builder(spec, args):
        if spec.tool == "nmap":
            return f"nmap -sV -oX - {args['target']}"
        if spec.tool == "curl":
            return f"curl -sS -o /dev/null -w '%{{http_code}}' {args['url']}"
        return spec.tool

    run_dir = tmp_path / "run"
    ssh = FakeSSH()
    bus = EventBus()
    controller = MissionController(
        mission_id="m1",
        playbook=pb,
        ssh=ssh,
        run_dir=run_dir,
        bus=bus,
        command_builder=builder,
    )
    await controller.run()

    events_path = run_dir / "events.jsonl"
    assert events_path.exists()
    lines = events_path.read_text().strip().splitlines()
    types = [json.loads(line)["event_type"] for line in lines]
    assert "mission_started" in types
    assert "mission_complete" in types
    assert types.count("fact_emitted") >= 4
    assert "expansion_fired" in types

    nmap_cmds = [c for c in ssh.last_commands if "nmap" in c]
    curl_cmds = [c for c in ssh.last_commands if "curl" in c]
    assert len(nmap_cmds) == 1
    assert len(curl_cmds) == 2

    runs_dir = run_dir / "tool_runs"
    stdout_files = list(runs_dir.glob("*.stdout"))
    assert len(stdout_files) == 3
