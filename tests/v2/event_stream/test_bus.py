"""Tests for the async event bus."""
from __future__ import annotations

import asyncio

import pytest

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.types import Event, EventType


@pytest.mark.asyncio
async def test_subscribe_and_publish_delivers_to_matching_handler():
    bus = EventBus()
    received: list[Event] = []

    async def handler(e: Event) -> None:
        received.append(e)

    bus.subscribe(handler, event_type=EventType.MISSION_STARTED)
    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    assert len(received) == 1
    assert received[0].event_type == EventType.MISSION_STARTED


@pytest.mark.asyncio
async def test_wildcard_subscriber_receives_all_events():
    bus = EventBus()
    received: list[Event] = []

    async def handler(e: Event) -> None:
        received.append(e)

    bus.subscribe(handler)
    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    await bus.publish(Event(event_type=EventType.TASK_RUNNING, mission_id="m1"))
    assert len(received) == 2


@pytest.mark.asyncio
async def test_typed_subscriber_ignores_other_types():
    bus = EventBus()
    received: list[Event] = []

    async def handler(e: Event) -> None:
        received.append(e)

    bus.subscribe(handler, event_type=EventType.MISSION_STARTED)
    await bus.publish(Event(event_type=EventType.TASK_RUNNING, mission_id="m1"))
    assert received == []


@pytest.mark.asyncio
async def test_handler_exceptions_do_not_break_other_handlers():
    bus = EventBus()
    received: list[Event] = []

    async def bad(_: Event) -> None:
        raise RuntimeError("boom")

    async def good(e: Event) -> None:
        received.append(e)

    bus.subscribe(bad)
    bus.subscribe(good)
    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    assert len(received) == 1


@pytest.mark.asyncio
async def test_multiple_handlers_receive_concurrently():
    bus = EventBus()
    counter = {"n": 0}

    async def handler(e: Event) -> None:
        await asyncio.sleep(0)
        counter["n"] += 1

    for _ in range(5):
        bus.subscribe(handler)
    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    assert counter["n"] == 5
