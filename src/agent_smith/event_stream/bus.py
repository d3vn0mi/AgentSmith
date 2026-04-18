"""In-process async pub/sub event bus for the v2 engine."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from agent_smith.event_stream.types import Event, EventType

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType | None, list[Handler]] = defaultdict(list)

    def subscribe(
        self,
        handler: Handler,
        event_type: EventType | None = None,
    ) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        handlers = self._subscribers.get(event.event_type, []) + self._subscribers.get(None, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for r, h in zip(results, handlers, strict=True):
            if isinstance(r, Exception):
                logger.warning("handler %s raised %s", getattr(h, "__name__", h), r)
