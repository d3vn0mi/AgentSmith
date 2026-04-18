"""Agent container entrypoint. Loads mission, runs agent, emits events."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import traceback
from pathlib import Path

import hashlib

from agent_smith.agent_runner.bridge import EventBridge
from agent_smith.agent_runner.event_writer import EventWriter
from agent_smith.control import crypto, registry
from agent_smith.events import EventBus


def _build_substitutions(mission, profile) -> dict[str, str]:
    """Mission-scope placeholder substitutions for v2 playbook root args."""
    return {
        "${TARGET}": mission.target,
        "${MISSION_SHORT_ID}": mission.id[:8],
        "${MISSION_RANGE_OFFSET}": str(
            int.from_bytes(
                hashlib.sha256(mission.id.encode()).digest()[:4], "big"
            ) % 80
        ),
        "${CALLBACK_IP}": getattr(profile, "callback_ip", None) or "",
    }


async def _cleanup_kali_sessions(mission_id: str, ssh) -> None:
    """Best-effort teardown of all tmux sessions this mission created on Kali.

    Called from the v2 engine's finally block. Never raises — silent failure
    if Kali is unreachable at shutdown is acceptable (operator can clean up
    by hand via the agentsmith-<short_id>- naming convention).
    """
    try:
        prefix = f"agentsmith-{mission_id[:8]}-"
        cmd = (
            f"tmux ls 2>/dev/null | "
            f"grep -o '^{prefix}[^:]*' | "
            f"xargs -r -I{{}} tmux kill-session -t {{}} 2>/dev/null"
        )
        await ssh.run_command(cmd, timeout=10)
    except Exception:
        return


def _resolve_engine(mission) -> str:
    """Return 'v2' if the mission's playbook loads via the v2 loader, else 'v1'."""
    try:
        from agent_smith.scenarios.loader import load_playbook
        pb_path = Path("src/agent_smith/playbooks") / mission.playbook
        if not pb_path.is_file():
            return "v1"
        load_playbook(pb_path)
        return "v2"
    except Exception:
        return "v1"


async def _build_and_run_agent(mission, profile, data_dir: Path, writer: EventWriter,
                                bus: EventBus):
    """Wire SSHConnection + AgentSmith and run it.

    Isolated for test substitution.
    """
    secret = crypto.decrypt(profile.credential_enc)

    from agent_smith.core.agent import AgentSmith
    from agent_smith.core.config import load_config
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


async def _run_v2_engine(mission, profile, data_dir: Path, writer) -> None:
    """Run the mission via the v2 MissionController + V2EventBridge."""
    from agent_smith.agent_runner.v2_bridge import V2EventBridge
    from agent_smith.controller import MissionController
    from agent_smith.event_stream.bus import EventBus as V2Bus
    from agent_smith.scenarios.loader import load_playbook
    from agent_smith.transport.ssh import SSHConnection

    # Decrypt SSH credential. Use the same key/password logic as legacy.
    from agent_smith.control import crypto as _crypto
    secret = _crypto.decrypt(profile.credential_enc)
    if profile.auth_type == "key":
        keyfile = Path("/tmp/agent_kali_key")
        keyfile.write_text(secret)
        keyfile.chmod(0o600)
        ssh = SSHConnection(
            host=profile.host, user=profile.username,
            key_path=str(keyfile), password=None,
        )
    else:
        ssh = SSHConnection(
            host=profile.host, user=profile.username,
            key_path=None, password=secret,
        )

    pb_path = Path("src/agent_smith/playbooks") / mission.playbook
    pb = load_playbook(pb_path)

    # Pre-substitute placeholders in root task args so the command template
    # renders the correct values. The v2 engine runs commands on the remote SSH
    # host via asyncssh (no shell env forwarding), so substitution must
    # happen locally before the command is built.
    SUBSTITUTIONS = _build_substitutions(mission, profile)
    for root in pb.root_tasks:
        for k, v in list(root.args.items()):
            if isinstance(v, str):
                for ph, val in SUBSTITUTIONS.items():
                    v = v.replace(ph, val)
                root.args[k] = v

    mission_dir = data_dir / "missions" / mission.id
    bus = V2Bus()
    bridge = V2EventBridge(bus, writer, mission_dir)
    await bridge.start()

    try:
        await ssh.connect()
        controller = MissionController(
            mission_id=mission.id,
            playbook=pb,
            ssh=ssh,
            run_dir=mission_dir / "v2",
            bus=bus,
        )
        await controller.run()
    finally:
        try:
            await _cleanup_kali_sessions(mission.id, ssh)
        except Exception:
            pass
        try:
            await ssh.disconnect()
        except Exception:
            pass
        await bridge.stop()


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
    mission_dir = events_path.parent

    stopped = {"flag": False}
    def _sigterm(*_a):
        stopped["flag"] = True
        writer.emit("mission.stopped", {"reason": "SIGTERM"})
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    writer.emit("mission.started", {})
    try:
        if _resolve_engine(mission) == "v2":
            await _run_v2_engine(mission, profile, data_dir, writer)
        else:
            bus = EventBus()
            bridge = EventBridge(bus, writer, mission_dir)
            await bridge.start()
            try:
                await _build_and_run_agent(mission, profile, data_dir, writer, bus)
            finally:
                await bridge.stop()
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    mission_id = os.environ["MISSION_ID"]
    agent_id = os.environ["AGENT_ID"]
    db_path = Path(os.environ.get("REGISTRY_DB", "data/registry.db"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    asyncio.run(run(db_path=db_path, data_dir=data_dir,
                     mission_id=mission_id, agent_id=agent_id))
