"""FastAPI application assembly with auth middleware."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

import docker
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agent_smith.auth.dependencies import configure_auth, get_ws_user
from agent_smith.auth.models import User, UserStore
from agent_smith.control import crypto, recovery, registry
from agent_smith.control.spawner import Spawner
from agent_smith.core.config import Config
from agent_smith.events import EventBus
from agent_smith.server.auth_routes import configure_auth_routes, router as auth_router
from agent_smith.server.routes import configure_routes, router as api_router
from agent_smith.server.v2_routes import router as v2_router
from agent_smith.server.websocket import WebSocketHub


def create_app(
    config: Config,
    event_bus: EventBus,
    get_agent_fn=None,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="AgentSmith - Puppet Master",
        description="Autonomous pentesting agent dashboard",
        version="0.1.0",
    )

    # Configure user store
    user_store = UserStore(config.auth.users_file)

    # Configure auth
    configure_auth(config.auth.jwt_secret, user_store)
    configure_auth_routes(
        jwt_secret=config.auth.jwt_secret,
        access_expiry=config.auth.access_token_expiry,
        refresh_expiry=config.auth.refresh_token_expiry,
        user_store=user_store,
    )

    # Configure API routes
    if get_agent_fn:
        configure_routes(get_agent_fn)

    # Register routers
    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(v2_router)

    # WebSocket hub
    ws_hub = WebSocketHub(event_bus)

    @app.on_event("startup")
    async def startup():
        await ws_hub.start()

    @app.on_event("shutdown")
    async def shutdown():
        await ws_hub.stop()

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        user: Annotated[User, Depends(get_ws_user)],
    ):
        await ws_hub.connect(websocket)
        try:
            while True:
                # Keep connection alive, handle client messages
                data = await websocket.receive_text()
                # Client can send ping or control messages
        except WebSocketDisconnect:
            ws_hub.disconnect(websocket)

    # Serve static files (dashboard)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        @app.get("/")
        async def serve_dashboard():
            return FileResponse(static_dir / "index.html")

        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


def _ensure_master_key(key_path: Path = Path("data/master_key")) -> str:
    """Return the MASTER_KEY, generating and persisting it on first run.

    Precedence: env var (explicit operator override) > on-disk file > newly
    generated. Persisted to the shared ./data volume so it survives
    control-plane restarts (env_file .env is read-only inside the container).
    """
    env_key = os.environ.get("MASTER_KEY")
    if env_key:
        return env_key

    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        key_str = key_path.read_text().strip()
        if key_str:
            os.environ["MASTER_KEY"] = key_str
            return key_str

    key_str = crypto.generate_key().decode()
    key_path.write_text(key_str)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    os.environ["MASTER_KEY"] = key_str
    logger = logging.getLogger("agent_smith")
    logger.warning(
        "Generated new MASTER_KEY and persisted to %s. "
        "BACK THIS UP — losing it makes all saved Kali creds unrecoverable.",
        key_path,
    )
    return key_str


def create_control_plane_app(config: Config) -> FastAPI:
    """Build the FastAPI app for the control-plane process."""
    db_path = Path("data/registry.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    reg = registry.Registry(str(db_path))
    reg.migrate()

    master_key = _ensure_master_key()

    docker_client = docker.from_env()
    spawner = Spawner(
        client=docker_client,
        image=os.environ.get("AGENT_IMAGE", "agentsmith:latest"),
        network=os.environ.get("AGENT_NETWORK", "agentsmith_internal"),
        data_dir_host=os.environ.get(
            "DATA_DIR_HOST", str(Path("data").resolve())),
        config_path_host=os.environ.get(
            "CONFIG_PATH_HOST", str(Path("config.yaml").resolve())),
        master_key=master_key,
        extra_env={k: v for k, v in os.environ.items()
                    if k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                              "OLLAMA_BASE_URL")},
    )

    data_dir = Path("data")
    recovery.reconcile(reg, spawner, data_dir=data_dir)

    import asyncio
    from contextlib import asynccontextmanager

    reconcile_interval = float(os.environ.get("RECONCILE_INTERVAL", "5"))

    @asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(recovery.reconcile_forever(
            reg, spawner, data_dir=data_dir, interval=reconcile_interval))
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="AgentSmith Control Plane", lifespan=lifespan)

    user_store = UserStore(config.auth.users_file)
    configure_auth_routes(
        jwt_secret=config.auth.jwt_secret,
        access_expiry=config.auth.access_token_expiry,
        refresh_expiry=config.auth.refresh_token_expiry,
        user_store=user_store,
    )
    app.include_router(auth_router)

    # Deferred imports — these modules are added in Tasks 12 and 13.
    from agent_smith.server.profile_routes import (
        router as profile_router, configure as configure_profile_routes)
    from agent_smith.server.mission_routes import (
        router as mission_router, configure as configure_mission_routes)
    configure_profile_routes(reg)
    configure_mission_routes(reg, spawner, data_dir=data_dir)
    app.include_router(profile_router)
    app.include_router(mission_router)

    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True),
               name="static")

    return app
