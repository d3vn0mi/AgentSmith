"""WebSocket connection manager for real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

from agent_smith.events import Event, EventBus

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._connections: list[WebSocket] = []
        self._broadcast_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the broadcast loop."""
        self._queue = self.event_bus.subscribe()
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self) -> None:
        """Stop the broadcast loop."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        self.event_bus.unsubscribe(self._queue)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections = [ws for ws in self._connections if ws is not websocket]
        logger.info("WebSocket client disconnected (%d remaining)", len(self._connections))

    async def _broadcast_loop(self) -> None:
        """Read events from the bus and broadcast to all WebSocket clients."""
        while True:
            try:
                event = await self._queue.get()
                await self._broadcast(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Broadcast error: %s", e)

    async def _broadcast(self, event: Event) -> None:
        """Send an event to all connected WebSocket clients."""
        if not self._connections:
            return

        message = json.dumps({
            "type": event.type,
            "data": event.data,
            "timestamp": event.timestamp,
        }, default=str)

        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def send_to(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception:
            self.disconnect(websocket)
