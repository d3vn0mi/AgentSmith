"""Control-plane process entrypoint (FastAPI server + registry only)."""
from __future__ import annotations

import logging
import sys

import uvicorn
from dotenv import load_dotenv

from agent_smith.core.config import load_config
from agent_smith.server.app import create_control_plane_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent_smith")


def run_control_plane(args: list[str]) -> None:
    load_dotenv()
    config_path = "config.yaml"
    for i, arg in enumerate(args):
        if arg in ("--config", "-c") and i + 1 < len(args):
            config_path = args[i + 1]

    config = load_config(config_path)
    app = create_control_plane_app(config)
    uvicorn.run(app, host=config.server.host, port=config.server.port,
                 log_level="info")


if __name__ == "__main__":
    run_control_plane(sys.argv[1:])
