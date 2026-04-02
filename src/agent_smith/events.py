"""Event bus for decoupling agent core from the web dashboard."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Event:
    type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Async event bus using asyncio.Queue for each subscriber."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []
        self._handlers: dict[str, list[Callable[..., Coroutine]]] = {}

    def subscribe(self) -> asyncio.Queue[Event]:
        """Create a new subscription queue. Returns queue to read events from."""
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        """Remove a subscription queue."""
        self._subscribers = [q for q in self._subscribers if q is not queue]

    def on(self, event_type: str, handler: Callable[..., Coroutine]) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all subscribers and registered handlers."""
        event = Event(type=event_type, data=data or {})

        # Push to all subscriber queues
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop event if subscriber is too slow

        # Call registered handlers
        for handler in self._handlers.get(event_type, []):
            try:
                await handler(event)
            except Exception:
                pass  # Don't let handler errors break the bus
