"""FastAPI application assembly with auth middleware."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agent_smith.auth.dependencies import configure_auth, get_ws_user
from agent_smith.auth.models import User, UserStore
from agent_smith.core.config import Config
from agent_smith.events import EventBus
from agent_smith.server.auth_routes import configure_auth_routes, router as auth_router
from agent_smith.server.routes import configure_routes, router as api_router
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
