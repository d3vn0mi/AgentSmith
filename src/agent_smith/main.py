"""Entry point - starts the agent and web server."""

from __future__ import annotations

import asyncio
import logging
import sys

import uvicorn
from dotenv import load_dotenv

from agent_smith.core.agent import AgentSmith
from agent_smith.core.config import load_config
from agent_smith.events import EventBus
from agent_smith.llm.factory import create_provider
from agent_smith.server.app import create_app
from agent_smith.tools.base import ToolRegistry
from agent_smith.tools.exploit import ExploitTool
from agent_smith.tools.file_ops import FileOpsTool
from agent_smith.tools.gobuster import GobusterTool
from agent_smith.tools.nmap import NmapTool
from agent_smith.tools.shell import ShellTool
from agent_smith.transport.ssh import SSHConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent_smith")


def build_tool_registry() -> ToolRegistry:
    """Register all available pentesting tools."""
    registry = ToolRegistry()
    registry.register(ShellTool())
    registry.register(NmapTool())
    registry.register(GobusterTool())
    registry.register(FileOpsTool())
    registry.register(ExploitTool())
    return registry


async def run_agent_and_server(config_path: str = "config.yaml") -> None:
    """Main entry point: run both the agent and the web dashboard."""
    load_dotenv()
    config = load_config(config_path)

    event_bus = EventBus()
    tools = build_tool_registry()
    llm = create_provider(config.llm)

    ssh = SSHConnection(
        host=config.attack_box.host,
        user=config.attack_box.user,
        key_path=config.attack_box.key_path if config.attack_box.key_path else None,
        password=config.attack_box.password if config.attack_box.password else None,
    )

    agent: AgentSmith | None = None

    def get_agent() -> AgentSmith | None:
        return agent

    app = create_app(config, event_bus, get_agent)

    # Start uvicorn server
    server_config = uvicorn.Config(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)

    # Run server in background
    server_task = asyncio.create_task(server.serve())

    logger.info("Dashboard available at http://%s:%d", config.server.host, config.server.port)

    # Connect SSH and start agent
    if config.attack_box.host and config.target.ip:
        try:
            await ssh.connect()
            agent = AgentSmith(config, llm, ssh, tools, event_bus)
            logger.info("Starting autonomous agent against %s", config.target.ip)
            agent_task = asyncio.create_task(agent.run())

            # Wait for either to finish
            done, pending = await asyncio.wait(
                [server_task, agent_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        finally:
            await ssh.disconnect()
            await llm.close()
    else:
        logger.info("No target/attack_box configured. Running dashboard only.")
        await server_task


def main() -> None:
    """CLI entry point."""
    args = sys.argv[1:]

    if args and args[0] == "seed-admin":
        # Seed admin user
        load_dotenv()
        config = load_config(args[1] if len(args) > 1 else "config.yaml")
        from agent_smith.auth.seed import seed_admin
        seed_admin(config.auth.users_file)
        return

    config_path = "config.yaml"
    for i, arg in enumerate(args):
        if arg in ("--config", "-c") and i + 1 < len(args):
            config_path = args[i + 1]

    asyncio.run(run_agent_and_server(config_path))


if __name__ == "__main__":
    main()
