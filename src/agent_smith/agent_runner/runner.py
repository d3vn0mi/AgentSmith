"""Agent container entrypoint. Loads mission, runs agent, emits events."""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import traceback
from pathlib import Path

from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.control import crypto, registry


async def _build_and_run_agent(mission, profile, data_dir: Path, writer: EventWriter):
    """Wire SSHConnection + AgentSmith and run it.

    Isolated for test substitution.
    """
    secret = crypto.decrypt(profile.credential_enc)

    from agent_smith.core.agent import AgentSmith
    from agent_smith.core.config import load_config
    from agent_smith.events import EventBus
    from agent_smith.llm.factory import create_provider
    from agent_smith.tools.base import ToolRegistry
    from agent_smith.tools.exploit import ExploitTool
    from agent_smith.tools.file_ops import FileOpsTool
    from agent_smith.tools.gobuster import GobusterTool
    from agent_smith.tools.nmap import NmapTool
    from agent_smith.tools.shell import ShellTool
    from agent_smith.transport.ssh import SSHConnection

    config = load_config("config.yaml")
    config.target.ip = mission.target
    config.attack_box.host = profile.host
    config.attack_box.user = profile.username
    if profile.auth_type == "key":
        keyfile = Path("/tmp/agent_kali_key")
        keyfile.write_text(secret)
        keyfile.chmod(0o600)
        config.attack_box.key_path = str(keyfile)
        config.attack_box.password = None
    else:
        config.attack_box.key_path = None
        config.attack_box.password = secret

    for k, v in (mission.agent_config or {}).items():
        if hasattr(config.agent, k):
            setattr(config.agent, k, v)

    bus = EventBus()
    tools = ToolRegistry()
    tools.register(ShellTool())
    tools.register(NmapTool())
    tools.register(GobusterTool())
    tools.register(FileOpsTool())
    tools.register(ExploitTool())

    llm = create_provider(config.llm)
    ssh = SSHConnection(
        host=config.attack_box.host, user=config.attack_box.user,
        key_path=config.attack_box.key_path, password=config.attack_box.password,
    )
    try:
        await ssh.connect()
        agent = AgentSmith(config, llm, ssh, tools, bus)
        await agent.run()
    finally:
        await ssh.disconnect()
        await llm.close()


async def run(*, db_path: Path, data_dir: Path, mission_id: str, agent_id: str) -> None:
    r = registry.Registry(str(db_path))
    try:
        mission = r.get_mission(mission_id)
        if mission is None:
            raise RuntimeError(f"mission {mission_id} not found")
        profile = r.get_profile(mission.kali_profile_id)
        if profile is None:
            raise RuntimeError(f"profile {mission.kali_profile_id} not found")
    finally:
        r.close()

    events_path = data_dir / "missions" / mission_id / "events.jsonl"
    writer = EventWriter(events_path, mission_id=mission_id, agent_id=agent_id)

    stopped = {"flag": False}
    def _sigterm(*_a):
        stopped["flag"] = True
        writer.emit("mission.stopped", {"reason": "SIGTERM"})
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    writer.emit("mission.started", {})
    try:
        await _build_and_run_agent(mission, profile, data_dir, writer)
    except SystemExit:
        raise
    except BaseException as exc:
        tb = traceback.format_exc()
        writer.emit("mission.failed", {"error": str(exc),
                                          "trace_truncated": tb[-4000:]})
        writer.close()
        sys.exit(1)

    if not stopped["flag"]:
        writer.emit("mission.completed", {"summary": ""})
    writer.close()


def main() -> None:
    mission_id = os.environ["MISSION_ID"]
    agent_id = os.environ["AGENT_ID"]
    db_path = Path(os.environ.get("REGISTRY_DB", "data/registry.db"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    asyncio.run(run(db_path=db_path, data_dir=data_dir,
                     mission_id=mission_id, agent_id=agent_id))
