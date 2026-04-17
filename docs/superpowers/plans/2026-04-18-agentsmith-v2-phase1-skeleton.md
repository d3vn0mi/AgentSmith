# AgentSmith v2 — Phase 1: Engine Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the DAG-based scenario engine skeleton — typed event stream, typed evidence store, mission graph + scheduler, YAML playbook loader, executor with generic shell + nmap parser, and a minimal API — demonstrable by running a skeleton port-scan playbook end-to-end against a Kali attack box.

**Architecture:** New modules (`event_stream/`, `evidence/`, `graph/`, `scenarios/`, `executor/`, `controller.py`) coexist with the current HTB loop under `src/agent_smith/`. Existing FastAPI dashboard, JWT auth, SSH transport, LLM providers, Docker deploy all unchanged. Phase 1 ships with **no LLM calls at all** — the full three-tier router and all its cost discipline lives in Phase 2. Phase 1 proves the engine mechanics: YAML playbook → root task → SSH execution → nmap parser → typed facts → expansion rules fire → new tasks → events emitted.

**Tech Stack:** Python 3.11+, pydantic v2 (already in deps), pyyaml, pytest + pytest-asyncio, asyncssh (existing), FastAPI (existing).

**Non-goals for Phase 1** (deferred to later phases — do **not** add them):
- The three-tier decision router (Phase 2).
- Scope guard, risk classifier, approval queue (Phase 2 backend, Phase 4 UI).
- Prompt caching, cost meter, rolling summary (Phase 2).
- Parsers beyond nmap (Phase 2 adds 5 more; Phase 3 adds the rest).
- Exploitation, credential discovery, recurrent expansion end-to-end (Phase 3).
- Mindmap panel, evidence panel with filters, approval queue UI, assessment overview, trend panel (Phase 4).
- Strict mode, mission-halt UX, failure-recovery polish, smoke tests against real targets (Phase 5).

If you catch yourself writing one of these, stop and note it for the next phase plan.

---

## File Structure

Every file created by Phase 1. Nothing below is "may create"; every entry is a concrete deliverable.

**New modules under `src/agent_smith/`:**

| Path | Responsibility |
|---|---|
| `event_stream/__init__.py` | Package init. |
| `event_stream/types.py` | `EventType` enum, `Event` pydantic model, event payload schemas. |
| `event_stream/bus.py` | `EventBus` with async pub/sub, per-mission subscriptions. |
| `event_stream/persistence.py` | `JsonlEventPersister` — subscriber that appends events to `data/runs/{mission_id}/events.jsonl`. |
| `evidence/__init__.py` | Package init, re-exports fact types. |
| `evidence/facts.py` | `Fact` base, `Provenance`, MVP fact types: `Host`, `OpenPort`, `WebEndpoint`. |
| `evidence/matcher.py` | `Predicate` parser + evaluator for fact-shape matching. |
| `evidence/store.py` | `EvidenceStore` — insert, dedup-by-key, supersede, typed query, subscribe-on-insert. |
| `graph/__init__.py` | Package init. |
| `graph/task.py` | `TaskState` enum, `Task` dataclass. |
| `graph/mission_graph.py` | `MissionGraph` — nodes, edges, state transitions, queries. |
| `graph/scheduler.py` | `Scheduler` — walks ready tasks; serial dispatch in Phase 1. |
| `scenarios/__init__.py` | Package init. |
| `scenarios/playbook.py` | `Playbook`, `TaskTypeSpec`, `ExpansionRule`, `TerminationRule` dataclasses. |
| `scenarios/loader.py` | YAML → `Playbook` with schema validation. |
| `scenarios/expansion.py` | Compile expansion rules; evaluate on fact insert; emit new task specs. |
| `executor/__init__.py` | Package init. |
| `executor/parsers/__init__.py` | Parser registry (`get_parser(tool) -> Parser | None`). |
| `executor/parsers/base.py` | `Parser` protocol, `ToolRun` input dataclass. |
| `executor/parsers/nmap_parser.py` | Nmap XML parser → emits `Host` + `OpenPort` facts. |
| `executor/shell.py` | Generic shell runner over `SSHConnection`, captures stdout/stderr/exit. |
| `executor/executor.py` | Dispatch: resolve args from template, run via shell, route to parser, persist stdout/stderr. |
| `controller.py` | `MissionController` — ties playbook, graph, evidence, executor, events; runs a mission end-to-end. |
| `server/v2_routes.py` | `/api/v2/assessments` — create, list, get-graph. |

**New data under `src/agent_smith/playbooks/`:**

| Path | Responsibility |
|---|---|
| `playbooks/__init__.py` | Makes the directory a package for resource lookup. |
| `playbooks/skeleton_portscan.yaml` | Phase 1 demo playbook: port-scan a scope, expand web ports into a noop "web probe" task, terminate when scope exhausted. |

**New tests under `tests/v2/`** (kept in a subdir so existing tests stay untouched):

| Path |
|---|
| `tests/v2/__init__.py` |
| `tests/v2/conftest.py` |
| `tests/v2/event_stream/test_types.py` |
| `tests/v2/event_stream/test_bus.py` |
| `tests/v2/event_stream/test_persistence.py` |
| `tests/v2/evidence/test_facts.py` |
| `tests/v2/evidence/test_matcher.py` |
| `tests/v2/evidence/test_store.py` |
| `tests/v2/graph/test_task.py` |
| `tests/v2/graph/test_mission_graph.py` |
| `tests/v2/graph/test_scheduler.py` |
| `tests/v2/scenarios/test_playbook.py` |
| `tests/v2/scenarios/test_loader.py` |
| `tests/v2/scenarios/test_expansion.py` |
| `tests/v2/executor/test_shell.py` |
| `tests/v2/executor/test_executor.py` |
| `tests/v2/executor/parsers/test_nmap_parser.py` |
| `tests/v2/test_controller.py` |
| `tests/v2/test_routes.py` |
| `tests/v2/integration/test_skeleton_portscan.py` |

**Modified existing files:**

| Path | Change |
|---|---|
| `src/agent_smith/server/app.py` | Mount the v2 router (no removal of v1 routes). |
| `pyproject.toml` | Add `jsonschema>=4.0` dep (for playbook YAML validation). |
| `README.md` | Add a "Phase 1 demo" section (Task 24). |

---

## Task 0: Create branch and verify environment

**Files:** None (git setup).

- [ ] **Step 1: Create a feature branch**

```bash
git checkout -b feat/phase1-engine-skeleton
```

- [ ] **Step 2: Verify test dependencies install**

```bash
pip install -e ".[dev]"
```

Expected: installs pytest, pytest-asyncio, pydantic v2, pyyaml, asyncssh cleanly.

- [ ] **Step 3: Run existing tests to confirm baseline passes**

```bash
PYTHONPATH=src pytest tests/ -x
```

Expected: all existing tests pass. If any fail, **stop** and fix/flag before adding new code.

- [ ] **Step 4: Add jsonschema dependency**

Edit `pyproject.toml`, replacing the `dependencies` block with:

```toml
dependencies = [
    "asyncssh>=2.17.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "websockets>=14.0",
    "anthropic>=0.45.0",
    "openai>=1.60.0",
    "httpx>=0.28.0",
    "pyyaml>=6.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.0",
    "python-jose[cryptography]>=3.3",
    "argon2-cffi>=23.1",
    "python-multipart>=0.0.9",
    "jsonschema>=4.0",
]
```

Then reinstall:

```bash
pip install -e ".[dev]"
```

- [ ] **Step 5: Create directory skeleton**

```bash
mkdir -p src/agent_smith/event_stream
mkdir -p src/agent_smith/evidence
mkdir -p src/agent_smith/graph
mkdir -p src/agent_smith/scenarios
mkdir -p src/agent_smith/executor/parsers
mkdir -p src/agent_smith/playbooks
mkdir -p tests/v2/event_stream
mkdir -p tests/v2/evidence
mkdir -p tests/v2/graph
mkdir -p tests/v2/scenarios
mkdir -p tests/v2/executor/parsers
mkdir -p tests/v2/integration
touch src/agent_smith/event_stream/__init__.py
touch src/agent_smith/evidence/__init__.py
touch src/agent_smith/graph/__init__.py
touch src/agent_smith/scenarios/__init__.py
touch src/agent_smith/executor/__init__.py
touch src/agent_smith/executor/parsers/__init__.py
touch src/agent_smith/playbooks/__init__.py
touch tests/v2/__init__.py
touch tests/v2/event_stream/__init__.py
touch tests/v2/evidence/__init__.py
touch tests/v2/graph/__init__.py
touch tests/v2/scenarios/__init__.py
touch tests/v2/executor/__init__.py
touch tests/v2/executor/parsers/__init__.py
touch tests/v2/integration/__init__.py
```

- [ ] **Step 6: Create shared test fixtures file**

Create `tests/v2/conftest.py`:

```python
"""Shared fixtures for Phase 1 v2 tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_run_dir(tmp_path: Path) -> Path:
    """A mission-run directory under pytest's tmp_path."""
    run_dir = tmp_path / "runs" / "test-mission"
    run_dir.mkdir(parents=True)
    return run_dir
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/agent_smith/ tests/v2/
git commit -m "chore(phase1): add dep + create module skeleton for v2 engine"
```

---

## Task 1: Event types

**Files:**
- Create: `src/agent_smith/event_stream/types.py`
- Test: `tests/v2/event_stream/test_types.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/event_stream/test_types.py`:

```python
"""Tests for typed events."""
from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from agent_smith.event_stream.types import Event, EventType


def test_event_types_cover_phase1_lifecycle():
    required = {
        "mission_started",
        "mission_complete",
        "mission_halted",
        "scenario_loaded",
        "task_created",
        "task_ready",
        "task_running",
        "task_complete",
        "task_failed",
        "expansion_fired",
        "tool_run_started",
        "tool_run_complete",
        "fact_emitted",
        "fact_updated",
    }
    assert required.issubset({e.value for e in EventType})


def test_event_has_stable_id_and_timestamp():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.event_id  # uuid populated
    assert e.timestamp <= time.time() + 1
    assert e.schema_version == 1


def test_event_task_id_is_optional():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.task_id is None


def test_event_rejects_unknown_type_string():
    with pytest.raises(ValidationError):
        Event.model_validate({"event_type": "not_a_real_type", "mission_id": "m1"})


def test_event_round_trips_through_json():
    original = Event(
        event_type=EventType.TASK_RUNNING,
        mission_id="m1",
        task_id="t1",
        payload={"cmd": "nmap -sV 1.2.3.4"},
    )
    wire = original.model_dump_json()
    restored = Event.model_validate_json(wire)
    assert restored.event_type == original.event_type
    assert restored.mission_id == "m1"
    assert restored.task_id == "t1"
    assert restored.payload["cmd"] == "nmap -sV 1.2.3.4"
    assert restored.event_id == original.event_id


def test_event_payload_defaults_to_empty_dict():
    e = Event(event_type=EventType.MISSION_STARTED, mission_id="m1")
    assert e.payload == {}
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_types.py -v
```

Expected: all tests fail with `ModuleNotFoundError: agent_smith.event_stream.types`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/event_stream/types.py`:

```python
"""Typed events produced by the v2 engine."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETE = "mission_complete"
    MISSION_HALTED = "mission_halted"
    SCENARIO_LOADED = "scenario_loaded"
    TASK_CREATED = "task_created"
    TASK_READY = "task_ready"
    TASK_RUNNING = "task_running"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    EXPANSION_FIRED = "expansion_fired"
    TOOL_RUN_STARTED = "tool_run_started"
    TOOL_RUN_COMPLETE = "tool_run_complete"
    TOOL_RUN_OUTPUT = "tool_run_output"
    FACT_EMITTED = "fact_emitted"
    FACT_UPDATED = "fact_updated"
    FACT_SUPERSEDED = "fact_superseded"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    mission_id: str
    task_id: str | None = None
    timestamp: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1

    model_config = {"extra": "forbid"}
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_types.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/event_stream/types.py tests/v2/event_stream/test_types.py
git commit -m "feat(phase1): typed Event model and EventType enum"
```

---

## Task 2: Event bus

**Files:**
- Create: `src/agent_smith/event_stream/bus.py`
- Test: `tests/v2/event_stream/test_bus.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/event_stream/test_bus.py`:

```python
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
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_bus.py -v
```

Expected: all tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/event_stream/bus.py`:

```python
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_bus.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/event_stream/bus.py tests/v2/event_stream/test_bus.py
git commit -m "feat(phase1): async event bus with typed and wildcard subscribers"
```

---

## Task 3: Event JSONL persistence

**Files:**
- Create: `src/agent_smith/event_stream/persistence.py`
- Test: `tests/v2/event_stream/test_persistence.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/event_stream/test_persistence.py`:

```python
"""Tests for JSONL event persistence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.persistence import JsonlEventPersister
from agent_smith.event_stream.types import Event, EventType


@pytest.mark.asyncio
async def test_persister_writes_event_to_jsonl(tmp_path: Path):
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=tmp_path)
    persister.attach(bus)

    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    await persister.flush()

    events_path = tmp_path / "events.jsonl"
    assert events_path.exists()
    lines = events_path.read_text().strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["event_type"] == "mission_started"
    assert obj["mission_id"] == "m1"


@pytest.mark.asyncio
async def test_persister_appends_multiple_events(tmp_path: Path):
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=tmp_path)
    persister.attach(bus)

    for i in range(3):
        await bus.publish(
            Event(event_type=EventType.TASK_RUNNING, mission_id="m1", task_id=f"t{i}")
        )
    await persister.flush()

    lines = (tmp_path / "events.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_persister_creates_run_dir_if_missing(tmp_path: Path):
    run_dir = tmp_path / "nested" / "run"
    bus = EventBus()
    persister = JsonlEventPersister(run_dir=run_dir)
    persister.attach(bus)

    await bus.publish(Event(event_type=EventType.MISSION_STARTED, mission_id="m1"))
    await persister.flush()

    assert (run_dir / "events.jsonl").exists()
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_persistence.py -v
```

Expected: `ModuleNotFoundError: agent_smith.event_stream.persistence`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/event_stream/persistence.py`:

```python
"""Event persistence: appends every event to events.jsonl in the mission run dir."""
from __future__ import annotations

import asyncio
from pathlib import Path

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.types import Event


class JsonlEventPersister:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self._file_path = run_dir / "events.jsonl"
        self._lock = asyncio.Lock()
        self._run_dir_ready = False

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(self._on_event, event_type=None)

    async def _on_event(self, event: Event) -> None:
        async with self._lock:
            if not self._run_dir_ready:
                self.run_dir.mkdir(parents=True, exist_ok=True)
                self._run_dir_ready = True
            with self._file_path.open("a", encoding="utf-8") as fh:
                fh.write(event.model_dump_json() + "\n")

    async def flush(self) -> None:
        return None
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/event_stream/test_persistence.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/event_stream/persistence.py tests/v2/event_stream/test_persistence.py
git commit -m "feat(phase1): JSONL event persister wired as bus subscriber"
```

---

## Task 4: Fact base class and Provenance

**Files:**
- Create: `src/agent_smith/evidence/facts.py` (base class portion)
- Test: `tests/v2/evidence/test_facts.py` (base class tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/evidence/test_facts.py`:

```python
"""Tests for the Fact base class and Provenance."""
from __future__ import annotations

import time

from agent_smith.evidence.facts import Fact, Provenance


def test_provenance_carries_task_run_parser_timestamp():
    p = Provenance(
        task_id="t1",
        tool_run_id="r1",
        parser="nmap",
        timestamp=123.0,
        snippet="22/tcp open ssh",
    )
    assert p.task_id == "t1"
    assert p.parser == "nmap"


def test_fact_base_defaults_id_confidence_timestamps():
    f = Fact(
        type="Host",
        payload={"ip": "1.2.3.4"},
        canonical_key="host:1.2.3.4",
    )
    assert f.id  # uuid generated
    assert f.confidence == 1.0
    assert f.superseded_by is None
    assert f.created_at <= time.time() + 1
    assert f.last_seen_at <= time.time() + 1


def test_fact_append_provenance_bumps_last_seen():
    f = Fact(type="Host", payload={"ip": "1.2.3.4"}, canonical_key="host:1.2.3.4")
    earlier = f.last_seen_at
    time.sleep(0.01)
    f.append_provenance(
        Provenance(task_id="t1", tool_run_id="r1", parser="nmap", timestamp=time.time(), snippet="x")
    )
    assert f.last_seen_at > earlier
    assert len(f.provenance) == 1
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_facts.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the base implementation**

Create `src/agent_smith/evidence/facts.py`:

```python
"""Typed facts emitted by the evidence store.

Each fact has a stable canonical_key for dedup, a confidence score,
and append-only provenance that tracks which task/tool/parser observed it.

MVP fact types (Host, OpenPort, WebEndpoint) live in this module too;
they are added in the next task.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provenance:
    task_id: str
    tool_run_id: str
    parser: str
    timestamp: float
    snippet: str


@dataclass
class Fact:
    type: str
    payload: dict[str, Any]
    canonical_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provenance: list[Provenance] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    superseded_by: str | None = None
    confidence: float = 1.0

    def append_provenance(self, p: Provenance) -> None:
        self.provenance.append(p)
        self.last_seen_at = time.time()
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_facts.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/evidence/facts.py tests/v2/evidence/test_facts.py
git commit -m "feat(phase1): Fact base class with Provenance"
```

---

## Task 5: MVP fact types (Host, OpenPort, WebEndpoint)

**Files:**
- Modify: `src/agent_smith/evidence/facts.py` (add three typed constructors)
- Modify: `src/agent_smith/evidence/__init__.py` (re-export)
- Modify: `tests/v2/evidence/test_facts.py` (add tests)

- [ ] **Step 1: Append failing tests**

Append to `tests/v2/evidence/test_facts.py`:

```python
from agent_smith.evidence.facts import Host, OpenPort, WebEndpoint


def test_host_fact_canonical_key_is_ip():
    h = Host.new(ip="10.0.0.5", hostname="srv", alive=True)
    assert h.type == "Host"
    assert h.canonical_key == "host:10.0.0.5"
    assert h.payload == {"ip": "10.0.0.5", "hostname": "srv", "os": None, "alive": True}


def test_host_fact_alive_defaults_true():
    h = Host.new(ip="10.0.0.5")
    assert h.payload["alive"] is True
    assert h.payload["hostname"] is None


def test_open_port_canonical_key_includes_protocol_and_number():
    p = OpenPort.new(host_ip="10.0.0.5", number=22, protocol="tcp", service="ssh")
    assert p.type == "OpenPort"
    assert p.canonical_key == "port:10.0.0.5:tcp:22"
    assert p.payload["service"] == "ssh"
    assert p.payload["version"] is None


def test_open_port_defaults_protocol_tcp():
    p = OpenPort.new(host_ip="10.0.0.5", number=80)
    assert p.payload["protocol"] == "tcp"
    assert p.payload["service"] is None


def test_web_endpoint_canonical_key_is_url():
    e = WebEndpoint.new(url="https://site/x", status=200, title="Admin", interesting=True)
    assert e.type == "WebEndpoint"
    assert e.canonical_key == "web:https://site/x"
    assert e.payload["title"] == "Admin"
    assert e.payload["interesting"] is True


def test_web_endpoint_interesting_defaults_false():
    e = WebEndpoint.new(url="https://site/x", status=404)
    assert e.payload["interesting"] is False
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_facts.py -v
```

Expected: 6 new failures (`ImportError: cannot import name 'Host'`).

- [ ] **Step 3: Extend `facts.py` with MVP fact types**

Append to `src/agent_smith/evidence/facts.py`:

```python
class Host:
    TYPE = "Host"

    @staticmethod
    def new(
        ip: str,
        hostname: str | None = None,
        os: str | None = None,
        alive: bool = True,
    ) -> Fact:
        return Fact(
            type=Host.TYPE,
            payload={"ip": ip, "hostname": hostname, "os": os, "alive": alive},
            canonical_key=f"host:{ip}",
        )


class OpenPort:
    TYPE = "OpenPort"

    @staticmethod
    def new(
        host_ip: str,
        number: int,
        protocol: str = "tcp",
        service: str | None = None,
        version: str | None = None,
    ) -> Fact:
        return Fact(
            type=OpenPort.TYPE,
            payload={
                "host_ip": host_ip,
                "number": number,
                "protocol": protocol,
                "service": service,
                "version": version,
            },
            canonical_key=f"port:{host_ip}:{protocol}:{number}",
        )


class WebEndpoint:
    TYPE = "WebEndpoint"

    @staticmethod
    def new(
        url: str,
        status: int,
        title: str | None = None,
        interesting: bool = False,
    ) -> Fact:
        return Fact(
            type=WebEndpoint.TYPE,
            payload={
                "url": url,
                "status": status,
                "title": title,
                "interesting": interesting,
            },
            canonical_key=f"web:{url}",
        )
```

- [ ] **Step 4: Update `evidence/__init__.py`**

Replace the empty `src/agent_smith/evidence/__init__.py` with:

```python
"""Typed evidence facts and store."""
from agent_smith.evidence.facts import Fact, Host, OpenPort, Provenance, WebEndpoint

__all__ = ["Fact", "Host", "OpenPort", "Provenance", "WebEndpoint"]
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_facts.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/agent_smith/evidence/facts.py src/agent_smith/evidence/__init__.py tests/v2/evidence/test_facts.py
git commit -m "feat(phase1): Host/OpenPort/WebEndpoint fact builders"
```

---

## Task 6: Fact matcher (predicate engine)

**Files:**
- Create: `src/agent_smith/evidence/matcher.py`
- Test: `tests/v2/evidence/test_matcher.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/evidence/test_matcher.py`:

```python
"""Tests for fact-shape predicate matching used by expansion rules."""
from __future__ import annotations

import pytest

from agent_smith.evidence.facts import Host, OpenPort, WebEndpoint
from agent_smith.evidence.matcher import parse_predicate


def test_parse_bare_type_matches_any_fact_of_that_type():
    pred = parse_predicate("Host")
    assert pred.type_name == "Host"
    assert pred.matches(Host.new(ip="1.2.3.4"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22))


def test_parse_predicate_with_equality_constraint():
    pred = parse_predicate("OpenPort{service: ssh}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))


def test_alternation_matches_either():
    pred = parse_predicate("OpenPort{service: http|https}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))


def test_present_and_absent():
    present = parse_predicate("OpenPort{service: present}")
    absent = parse_predicate("OpenPort{service: absent}")
    with_service = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    without_service = OpenPort.new(host_ip="1.2.3.4", number=22, service=None)
    assert present.matches(with_service)
    assert not present.matches(without_service)
    assert absent.matches(without_service)
    assert not absent.matches(with_service)


def test_numeric_range():
    pred = parse_predicate("OpenPort{number: 1-1024}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22))
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=1024))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=3000))


def test_regex_predicate():
    pred = parse_predicate("WebEndpoint{title: ~/admin/i}")
    assert pred.matches(WebEndpoint.new(url="https://x/1", status=200, title="Admin Panel"))
    assert pred.matches(WebEndpoint.new(url="https://x/2", status=200, title="admin"))
    assert not pred.matches(WebEndpoint.new(url="https://x/3", status=200, title="Home"))


def test_multiple_constraints_all_must_match():
    pred = parse_predicate("OpenPort{service: http|https, number: 1-65535}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="ssh"))


def test_invalid_syntax_raises():
    with pytest.raises(ValueError):
        parse_predicate("OpenPort{service ssh}")
    with pytest.raises(ValueError):
        parse_predicate("")
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_matcher.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/evidence/matcher.py`:

```python
"""Predicate engine for matching typed facts.

Syntax examples:
    Host
    OpenPort{service: ssh}
    OpenPort{service: http|https}
    OpenPort{service: present}
    OpenPort{service: absent}
    OpenPort{number: 1-1024}
    WebEndpoint{title: ~/admin/i}
    OpenPort{service: http|https, number: 1-65535}
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from agent_smith.evidence.facts import Fact


ConstraintFn = Callable[[Any], bool]


@dataclass
class Predicate:
    type_name: str
    constraints: dict[str, ConstraintFn]

    def matches(self, fact: Fact) -> bool:
        if fact.type != self.type_name:
            return False
        for key, check in self.constraints.items():
            if not check(fact.payload.get(key)):
                return False
        return True


def _build_value_check(expr: str) -> ConstraintFn:
    expr = expr.strip()

    if expr == "present":
        return lambda v: v is not None
    if expr == "absent":
        return lambda v: v is None

    if expr.startswith("~/"):
        m = re.match(r"~/(.+)/([iIsS]*)$", expr)
        if not m:
            raise ValueError(f"bad regex predicate: {expr!r}")
        flags = 0
        if "i" in m.group(2).lower():
            flags |= re.IGNORECASE
        if "s" in m.group(2).lower():
            flags |= re.DOTALL
        pat = re.compile(m.group(1), flags)
        return lambda v: isinstance(v, str) and pat.search(v) is not None

    range_m = re.match(r"^(-?\d+)-(-?\d+)$", expr)
    if range_m:
        lo = int(range_m.group(1))
        hi = int(range_m.group(2))
        return lambda v: isinstance(v, int) and lo <= v <= hi

    if "|" in expr:
        options = tuple(opt.strip() for opt in expr.split("|"))
        return lambda v: str(v) in options if v is not None else False

    return lambda v: str(v) == expr if v is not None else expr == "None"


def parse_predicate(text: str) -> Predicate:
    text = text.strip()
    if not text:
        raise ValueError("empty predicate")

    if "{" not in text:
        return Predicate(type_name=text, constraints={})

    head, _, rest = text.partition("{")
    type_name = head.strip()
    if not rest.endswith("}"):
        raise ValueError(f"missing closing brace: {text!r}")
    body = rest[:-1]

    constraints: dict[str, ConstraintFn] = {}
    if body.strip():
        parts = _split_top_level(body, sep=",")
        for part in parts:
            if ":" not in part:
                raise ValueError(f"constraint needs 'key: value' — got {part!r}")
            k, _, v = part.partition(":")
            constraints[k.strip()] = _build_value_check(v.strip())

    return Predicate(type_name=type_name, constraints=constraints)


def _split_top_level(s: str, sep: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    in_regex = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "~" and i + 1 < len(s) and s[i + 1] == "/":
            in_regex = True
            buf.append(c)
        elif in_regex and c == "/":
            in_regex = False
            buf.append(c)
        elif c == sep and not in_regex:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        out.append("".join(buf).strip())
    return [p for p in out if p]
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_matcher.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/evidence/matcher.py tests/v2/evidence/test_matcher.py
git commit -m "feat(phase1): predicate parser for expansion rule matching"
```

---

## Task 7: EvidenceStore

**Files:**
- Create: `src/agent_smith/evidence/store.py`
- Test: `tests/v2/evidence/test_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/evidence/test_store.py`:

```python
"""Tests for the EvidenceStore: dedup, supersede, queries, subscriptions."""
from __future__ import annotations

from agent_smith.evidence.facts import Host, OpenPort, Provenance
from agent_smith.evidence.matcher import parse_predicate
from agent_smith.evidence.store import EvidenceStore


def _prov(task: str = "t1") -> Provenance:
    return Provenance(
        task_id=task, tool_run_id="r1", parser="nmap", timestamp=0.0, snippet="x"
    )


def test_insert_new_fact_stores_it():
    s = EvidenceStore()
    f = Host.new(ip="1.2.3.4")
    f.append_provenance(_prov())
    result = s.insert(f)
    assert result.inserted is True
    assert result.fact is f
    assert len(s.all()) == 1


def test_insert_duplicate_key_merges_provenance():
    s = EvidenceStore()
    first = Host.new(ip="1.2.3.4")
    first.append_provenance(_prov("t1"))
    s.insert(first)

    second = Host.new(ip="1.2.3.4")
    second.append_provenance(_prov("t2"))
    result = s.insert(second)

    assert result.inserted is False
    assert result.fact.id == first.id
    assert len(result.fact.provenance) == 2


def test_supersede_when_payload_materially_differs():
    s = EvidenceStore()
    first = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    s.insert(first)

    second = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh", version="OpenSSH 8.9")
    result = s.insert(second)

    assert result.superseded is True
    assert first.superseded_by is not None
    live = s.by_type("OpenPort")
    assert len(live) == 1
    assert live[0].payload["version"] == "OpenSSH 8.9"


def test_by_type_only_returns_live_facts():
    s = EvidenceStore()
    f1 = Host.new(ip="1.2.3.4")
    f2 = Host.new(ip="5.6.7.8")
    s.insert(f1)
    s.insert(f2)
    assert {f.payload["ip"] for f in s.by_type("Host")} == {"1.2.3.4", "5.6.7.8"}


def test_by_predicate_returns_matching_live_facts():
    s = EvidenceStore()
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))

    web = s.by_predicate(parse_predicate("OpenPort{service: http|https}"))
    assert {f.payload["number"] for f in web} == {80, 443}


def test_subscribe_on_insert_invoked():
    s = EvidenceStore()
    seen = []
    s.on_insert(lambda result: seen.append(result))
    s.insert(Host.new(ip="1.2.3.4"))
    assert len(seen) == 1
    assert seen[0].inserted is True


def test_subscribe_on_supersede_also_invoked_on_update():
    s = EvidenceStore()
    events = []
    s.on_insert(lambda r: events.append(("insert", r.inserted, r.superseded)))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    s.insert(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh", version="OpenSSH 8.9"))
    assert events == [("insert", True, False), ("insert", False, True)]
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_store.py -v
```

Expected: all fail with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/evidence/store.py`:

```python
"""Typed evidence store: dedup by canonical_key, supersede on material change."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_smith.evidence.facts import Fact
from agent_smith.evidence.matcher import Predicate


@dataclass
class InsertResult:
    fact: Fact
    inserted: bool
    superseded: bool


InsertListener = Callable[[InsertResult], None]


class EvidenceStore:
    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}
        self._by_key: dict[str, str] = {}
        self._listeners: list[InsertListener] = []

    def on_insert(self, listener: InsertListener) -> None:
        self._listeners.append(listener)

    def insert(self, fact: Fact) -> InsertResult:
        existing_id = self._by_key.get(fact.canonical_key)
        if existing_id is None:
            self._facts[fact.id] = fact
            self._by_key[fact.canonical_key] = fact.id
            result = InsertResult(fact=fact, inserted=True, superseded=False)
        else:
            existing = self._facts[existing_id]
            if self._materially_different(existing.payload, fact.payload):
                existing.superseded_by = fact.id
                fact.provenance = existing.provenance + fact.provenance
                self._facts[fact.id] = fact
                self._by_key[fact.canonical_key] = fact.id
                result = InsertResult(fact=fact, inserted=False, superseded=True)
            else:
                for p in fact.provenance:
                    existing.append_provenance(p)
                result = InsertResult(fact=existing, inserted=False, superseded=False)

        for listener in self._listeners:
            listener(result)
        return result

    def all(self) -> list[Fact]:
        return [f for f in self._facts.values() if f.superseded_by is None]

    def by_type(self, type_name: str) -> list[Fact]:
        return [f for f in self.all() if f.type == type_name]

    def by_predicate(self, predicate: Predicate) -> list[Fact]:
        return [f for f in self.all() if predicate.matches(f)]

    def get(self, fact_id: str) -> Fact | None:
        return self._facts.get(fact_id)

    @staticmethod
    def _materially_different(old: dict, new: dict) -> bool:
        for k, v in new.items():
            if v is None:
                continue
            if old.get(k) != v:
                return True
        return False
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/evidence/test_store.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/evidence/store.py tests/v2/evidence/test_store.py
git commit -m "feat(phase1): EvidenceStore with dedup, supersede, predicate queries"
```

---

## Task 8: Task and TaskState

**Files:**
- Create: `src/agent_smith/graph/task.py`
- Test: `tests/v2/graph/test_task.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/graph/test_task.py`:

```python
"""Tests for Task and TaskState."""
from __future__ import annotations

import pytest

from agent_smith.graph.task import Task, TaskState


def test_task_starts_pending():
    t = Task(
        id="t1",
        task_type="port_scan",
        args={"host": "1.2.3.4"},
        consumes={},
        produces=["Host", "OpenPort"],
    )
    assert t.state == TaskState.PENDING


def test_transition_allowed_pending_to_ready():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    t.transition(TaskState.READY)
    assert t.state == TaskState.READY


def test_transition_disallowed_pending_to_complete():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    with pytest.raises(ValueError):
        t.transition(TaskState.COMPLETE)


def test_full_happy_path():
    t = Task(id="t1", task_type="x", args={}, consumes={}, produces=[])
    for s in [TaskState.READY, TaskState.RUNNING, TaskState.COMPLETE]:
        t.transition(s)
    assert t.state == TaskState.COMPLETE
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_task.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/graph/task.py`:

```python
"""Task and TaskState used by the Mission Graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_smith.evidence.facts import Fact


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


_ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.READY, TaskState.SKIPPED},
    TaskState.READY: {TaskState.AWAITING_APPROVAL, TaskState.RUNNING, TaskState.SKIPPED},
    TaskState.AWAITING_APPROVAL: {TaskState.RUNNING, TaskState.SKIPPED},
    TaskState.RUNNING: {TaskState.COMPLETE, TaskState.FAILED},
    TaskState.COMPLETE: set(),
    TaskState.FAILED: set(),
    TaskState.SKIPPED: set(),
}


@dataclass
class Task:
    id: str
    task_type: str
    args: dict[str, Any]
    consumes: dict[str, Fact]
    produces: list[str]
    state: TaskState = TaskState.PENDING
    triggered_by_rule: str | None = None
    triggered_by_fact_ids: list[str] = field(default_factory=list)
    parent_task_id: str | None = None
    created_at: float | None = None

    def transition(self, target: TaskState) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid transition: {self.state} -> {target}")
        self.state = target
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_task.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/graph/task.py tests/v2/graph/test_task.py
git commit -m "feat(phase1): Task dataclass + TaskState with transition guards"
```

---

## Task 9: MissionGraph

**Files:**
- Create: `src/agent_smith/graph/mission_graph.py`
- Test: `tests/v2/graph/test_mission_graph.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/graph/test_mission_graph.py`:

```python
"""Tests for the MissionGraph data structure."""
from __future__ import annotations

import pytest

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.task import Task, TaskState


def _task(id_: str, state: TaskState = TaskState.PENDING) -> Task:
    t = Task(id=id_, task_type="x", args={}, consumes={}, produces=[])
    t.state = state
    return t


def test_add_task_and_retrieve():
    g = MissionGraph(mission_id="m1")
    t = _task("t1")
    g.add_task(t)
    assert g.get("t1") is t
    assert list(g.all_tasks()) == [t]


def test_add_duplicate_task_raises():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1"))
    with pytest.raises(ValueError):
        g.add_task(_task("t1"))


def test_by_state_filters():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.READY))
    g.add_task(_task("t2", TaskState.PENDING))
    g.add_task(_task("t3", TaskState.READY))
    ready = {t.id for t in g.by_state(TaskState.READY)}
    assert ready == {"t1", "t3"}


def test_edges_are_recorded_when_task_has_parent():
    g = MissionGraph(mission_id="m1")
    parent = _task("t1")
    g.add_task(parent)
    child = _task("t2")
    child.parent_task_id = "t1"
    g.add_task(child)
    assert g.children_of("t1") == ["t2"]
    assert g.parent_of("t2") == "t1"


def test_total_and_finished_counts():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.COMPLETE))
    g.add_task(_task("t2", TaskState.PENDING))
    g.add_task(_task("t3", TaskState.FAILED))
    g.add_task(_task("t4", TaskState.SKIPPED))
    assert g.total() == 4
    assert g.finished() == 3
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_mission_graph.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/graph/mission_graph.py`:

```python
"""MissionGraph: typed tasks as nodes, parent->child as edges."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agent_smith.graph.task import Task, TaskState


_FINISHED = {TaskState.COMPLETE, TaskState.FAILED, TaskState.SKIPPED}


class MissionGraph:
    def __init__(self, mission_id: str) -> None:
        self.mission_id = mission_id
        self._tasks: dict[str, Task] = {}
        self._children: dict[str, list[str]] = {}

    def add_task(self, task: Task) -> None:
        if task.id in self._tasks:
            raise ValueError(f"duplicate task id: {task.id}")
        self._tasks[task.id] = task
        self._children.setdefault(task.id, [])
        if task.parent_task_id:
            self._children.setdefault(task.parent_task_id, []).append(task.id)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> Iterable[Task]:
        return self._tasks.values()

    def by_state(self, state: TaskState) -> list[Task]:
        return [t for t in self._tasks.values() if t.state == state]

    def children_of(self, task_id: str) -> list[str]:
        return list(self._children.get(task_id, []))

    def parent_of(self, task_id: str) -> str | None:
        t = self._tasks.get(task_id)
        return t.parent_task_id if t else None

    def total(self) -> int:
        return len(self._tasks)

    def finished(self) -> int:
        return sum(1 for t in self._tasks.values() if t.state in _FINISHED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "total": self.total(),
            "finished": self.finished(),
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "state": t.state.value,
                    "parent_task_id": t.parent_task_id,
                    "triggered_by_rule": t.triggered_by_rule,
                    "args": t.args,
                }
                for t in self._tasks.values()
            ],
        }
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_mission_graph.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/graph/mission_graph.py tests/v2/graph/test_mission_graph.py
git commit -m "feat(phase1): MissionGraph data structure"
```

---

## Task 10: Scheduler (serial, Phase 1)

**Files:**
- Create: `src/agent_smith/graph/scheduler.py`
- Test: `tests/v2/graph/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/graph/test_scheduler.py`:

```python
"""Tests for the Phase 1 serial scheduler."""
from __future__ import annotations

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.scheduler import Scheduler
from agent_smith.graph.task import Task, TaskState


def _task(id_: str, state: TaskState = TaskState.PENDING) -> Task:
    t = Task(id=id_, task_type="x", args={}, consumes={}, produces=[])
    t.state = state
    return t


def test_next_ready_returns_first_ready_task():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.COMPLETE))
    g.add_task(_task("t2", TaskState.READY))
    g.add_task(_task("t3", TaskState.READY))
    s = Scheduler(g)
    picked = s.next_ready()
    assert picked is not None
    assert picked.id == "t2"


def test_next_ready_returns_none_when_no_ready_tasks():
    g = MissionGraph(mission_id="m1")
    g.add_task(_task("t1", TaskState.PENDING))
    s = Scheduler(g)
    assert s.next_ready() is None


def test_has_outstanding_work_respects_pending_and_running():
    g = MissionGraph(mission_id="m1")
    s = Scheduler(g)
    assert not s.has_outstanding_work()

    g.add_task(_task("t1", TaskState.PENDING))
    assert s.has_outstanding_work()

    g.get("t1").state = TaskState.COMPLETE
    assert not s.has_outstanding_work()
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_scheduler.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/graph/scheduler.py`:

```python
"""Phase 1 serial scheduler.

Picks the first READY task in insertion order. Concurrency, OPSEC rate
limiting, and cost-aware scheduling arrive in Phase 2.
"""
from __future__ import annotations

from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.task import Task, TaskState


_OUTSTANDING = {TaskState.PENDING, TaskState.READY, TaskState.AWAITING_APPROVAL, TaskState.RUNNING}


class Scheduler:
    def __init__(self, graph: MissionGraph) -> None:
        self.graph = graph

    def next_ready(self) -> Task | None:
        for t in self.graph.all_tasks():
            if t.state == TaskState.READY:
                return t
        return None

    def has_outstanding_work(self) -> bool:
        return any(t.state in _OUTSTANDING for t in self.graph.all_tasks())
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/graph/test_scheduler.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/graph/scheduler.py tests/v2/graph/test_scheduler.py
git commit -m "feat(phase1): serial scheduler (Phase 1 concurrency policy)"
```

---

## Task 11: Playbook dataclasses

**Files:**
- Create: `src/agent_smith/scenarios/playbook.py`
- Test: `tests/v2/scenarios/test_playbook.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/scenarios/test_playbook.py`:

```python
"""Tests for playbook dataclasses."""
from __future__ import annotations

from agent_smith.scenarios.playbook import (
    ExpansionRule,
    Playbook,
    RootTaskSpec,
    TaskTypeSpec,
    TerminationRule,
)


def test_playbook_defaults_are_empty():
    p = Playbook(name="x", version="1.0")
    assert p.root_tasks == []
    assert p.task_types == {}
    assert p.expansions == []
    assert p.terminations == []
    assert p.cost_cap_usd is None


def test_task_type_spec_round_trip():
    spec = TaskTypeSpec(
        name="port_scan",
        consumes={"host": "Host"},
        produces=["OpenPort"],
        tool="nmap",
        args_template={"target": "{host.ip}"},
        risk="low",
        timeout=300,
        parser="nmap",
    )
    assert spec.name == "port_scan"
    assert spec.consumes == {"host": "Host"}


def test_expansion_rule_fields():
    rule = ExpansionRule(id="r1", on_fact="OpenPort{service: http}", spawn=["web_dir_enum"])
    assert rule.id == "r1"
    assert rule.spawn == ["web_dir_enum"]


def test_termination_rule_named():
    tr = TerminationRule(kind="scope_exhausted")
    assert tr.kind == "scope_exhausted"


def test_root_task_spec_carries_args():
    r = RootTaskSpec(task_type="port_scan", args={"host_set": ["1.2.3.4"]})
    assert r.task_type == "port_scan"
    assert r.args["host_set"] == ["1.2.3.4"]
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_playbook.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/scenarios/playbook.py`:

```python
"""Playbook data model — YAML-declarative scenarios."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskTypeSpec:
    name: str
    consumes: dict[str, str]
    produces: list[str]
    tool: str
    args_template: dict[str, Any]
    risk: str = "low"
    timeout: int = 300
    parser: str | None = None
    cache_key: str | None = None
    requires_tier2: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RootTaskSpec:
    task_type: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpansionRule:
    id: str
    on_fact: str | None = None
    on_fact_python: str | None = None
    spawn: list[str] = field(default_factory=list)


@dataclass
class TerminationRule:
    kind: str
    python_hook: str | None = None


@dataclass
class Playbook:
    name: str
    version: str
    scope_required: bool = False
    allowed_risks: list[str] = field(default_factory=lambda: ["low"])
    cost_cap_usd: float | None = None
    root_tasks: list[RootTaskSpec] = field(default_factory=list)
    task_types: dict[str, TaskTypeSpec] = field(default_factory=dict)
    expansions: list[ExpansionRule] = field(default_factory=list)
    terminations: list[TerminationRule] = field(default_factory=list)
    report_template: str | None = None
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_playbook.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/scenarios/playbook.py tests/v2/scenarios/test_playbook.py
git commit -m "feat(phase1): Playbook/TaskTypeSpec/ExpansionRule dataclasses"
```

---

## Task 12: Scenario loader

**Files:**
- Create: `src/agent_smith/scenarios/loader.py`
- Test: `tests/v2/scenarios/test_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/scenarios/test_loader.py`:

```python
"""Tests for the YAML playbook loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_smith.scenarios.loader import PlaybookValidationError, load_playbook


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def test_load_minimal_playbook(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: minimal
version: "1.0"
root_tasks:
  - port_scan:
      host_set: ["1.2.3.4"]
task_types:
  port_scan:
    consumes: {}
    produces: [Host, OpenPort]
    tool: nmap
    args_template:
      target: "{host}"
    parser: nmap
expansions: []
terminations:
  - scope_exhausted
""")
    pb = load_playbook(path)
    assert pb.name == "minimal"
    assert pb.root_tasks[0].task_type == "port_scan"
    assert pb.root_tasks[0].args == {"host_set": ["1.2.3.4"]}
    assert "port_scan" in pb.task_types
    assert pb.task_types["port_scan"].tool == "nmap"
    assert pb.terminations[0].kind == "scope_exhausted"


def test_load_playbook_with_expansions(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: with-rules
version: "1.0"
root_tasks: []
task_types:
  web_dir_enum:
    consumes:
      host: Host
      port: "OpenPort{service: http|https}"
    produces: [WebEndpoint]
    tool: feroxbuster
    args_template: {url: "{host.ip}"}
expansions:
  - id: http-enum
    on_fact: "OpenPort{service: http|https}"
    spawn: [web_dir_enum]
terminations: [scope_exhausted]
""")
    pb = load_playbook(path)
    assert len(pb.expansions) == 1
    assert pb.expansions[0].id == "http-enum"
    assert pb.expansions[0].spawn == ["web_dir_enum"]


def test_missing_required_field_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
version: "1.0"
root_tasks: []
task_types: {}
expansions: []
terminations: []
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)


def test_unknown_task_type_in_root_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: bad
version: "1.0"
root_tasks:
  - does_not_exist: {}
task_types:
  other:
    consumes: {}
    produces: []
    tool: nmap
    args_template: {}
expansions: []
terminations: [scope_exhausted]
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)


def test_unknown_spawn_in_expansion_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: bad
version: "1.0"
root_tasks: []
task_types:
  real:
    consumes: {}
    produces: []
    tool: nmap
    args_template: {}
expansions:
  - id: r1
    on_fact: "Host"
    spawn: [not_real]
terminations: [scope_exhausted]
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_loader.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/scenarios/loader.py`:

```python
"""YAML playbook loader with structural validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_smith.scenarios.playbook import (
    ExpansionRule,
    Playbook,
    RootTaskSpec,
    TaskTypeSpec,
    TerminationRule,
)


class PlaybookValidationError(Exception):
    pass


def load_playbook(path: str | Path) -> Playbook:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise PlaybookValidationError(f"playbook must be a mapping: {path}")

    for required in ("name", "version", "root_tasks", "task_types", "expansions", "terminations"):
        if required not in raw:
            raise PlaybookValidationError(f"missing required field: {required}")

    task_types = _load_task_types(raw["task_types"])
    root_tasks = _load_root_tasks(raw["root_tasks"], task_types)
    expansions = _load_expansions(raw["expansions"], task_types)
    terminations = _load_terminations(raw["terminations"])

    return Playbook(
        name=raw["name"],
        version=str(raw["version"]),
        scope_required=bool(raw.get("scope_required", False)),
        allowed_risks=list(raw.get("allowed_risks", ["low"])),
        cost_cap_usd=raw.get("cost_cap_usd"),
        root_tasks=root_tasks,
        task_types=task_types,
        expansions=expansions,
        terminations=terminations,
        report_template=raw.get("report_template"),
    )


def _load_task_types(raw: Any) -> dict[str, TaskTypeSpec]:
    if not isinstance(raw, dict):
        raise PlaybookValidationError("task_types must be a mapping")
    out: dict[str, TaskTypeSpec] = {}
    for name, body in raw.items():
        if not isinstance(body, dict):
            raise PlaybookValidationError(f"task_type {name!r}: body must be a mapping")
        for required in ("consumes", "produces", "tool", "args_template"):
            if required not in body:
                raise PlaybookValidationError(f"task_type {name!r}: missing {required}")
        out[name] = TaskTypeSpec(
            name=name,
            consumes=dict(body["consumes"]),
            produces=list(body["produces"]),
            tool=body["tool"],
            args_template=dict(body["args_template"]),
            risk=body.get("risk", "low"),
            timeout=int(body.get("timeout", 300)),
            parser=body.get("parser"),
            cache_key=body.get("cache_key"),
            requires_tier2=bool(body.get("requires_tier2", False)),
            metadata=dict(body.get("metadata", {})),
        )
    return out


def _load_root_tasks(raw: Any, task_types: dict[str, TaskTypeSpec]) -> list[RootTaskSpec]:
    if not isinstance(raw, list):
        raise PlaybookValidationError("root_tasks must be a list")
    out: list[RootTaskSpec] = []
    for entry in raw:
        if not isinstance(entry, dict) or len(entry) != 1:
            raise PlaybookValidationError(f"root_tasks entry must be a single-key mapping: {entry!r}")
        (ttype, args) = next(iter(entry.items()))
        if ttype not in task_types:
            raise PlaybookValidationError(f"root_tasks references unknown task_type: {ttype!r}")
        out.append(RootTaskSpec(task_type=ttype, args=dict(args or {})))
    return out


def _load_expansions(raw: Any, task_types: dict[str, TaskTypeSpec]) -> list[ExpansionRule]:
    if not isinstance(raw, list):
        raise PlaybookValidationError("expansions must be a list")
    out: list[ExpansionRule] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PlaybookValidationError(f"expansion entry must be a mapping: {entry!r}")
        rule = ExpansionRule(
            id=entry.get("id") or f"rule_{len(out) + 1}",
            on_fact=entry.get("on_fact"),
            on_fact_python=entry.get("on_fact_python"),
            spawn=list(entry.get("spawn", [])),
        )
        if not rule.on_fact and not rule.on_fact_python:
            raise PlaybookValidationError(f"expansion {rule.id!r}: on_fact or on_fact_python required")
        for tt in rule.spawn:
            if tt not in task_types:
                raise PlaybookValidationError(
                    f"expansion {rule.id!r}: spawn references unknown task_type {tt!r}"
                )
        out.append(rule)
    return out


def _load_terminations(raw: Any) -> list[TerminationRule]:
    if not isinstance(raw, list):
        raise PlaybookValidationError("terminations must be a list")
    out: list[TerminationRule] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(TerminationRule(kind=entry))
        elif isinstance(entry, dict):
            out.append(
                TerminationRule(
                    kind=entry.get("kind", "custom"),
                    python_hook=entry.get("python_hook"),
                )
            )
        else:
            raise PlaybookValidationError(f"termination entry unrecognized: {entry!r}")
    return out
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_loader.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/scenarios/loader.py tests/v2/scenarios/test_loader.py
git commit -m "feat(phase1): playbook YAML loader with structural validation"
```

---

## Task 13: Expansion engine

**Files:**
- Create: `src/agent_smith/scenarios/expansion.py`
- Test: `tests/v2/scenarios/test_expansion.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/scenarios/test_expansion.py`:

```python
"""Tests for the expansion engine."""
from __future__ import annotations

from agent_smith.evidence.facts import Host, OpenPort
from agent_smith.scenarios.expansion import ExpansionEngine, SpawnRequest
from agent_smith.scenarios.playbook import ExpansionRule, Playbook, TaskTypeSpec


def _playbook_with_web_rule() -> Playbook:
    return Playbook(
        name="x",
        version="1.0",
        task_types={
            "web_dir_enum": TaskTypeSpec(
                name="web_dir_enum",
                consumes={"host": "Host", "port": "OpenPort{service: http|https}"},
                produces=["WebEndpoint"],
                tool="feroxbuster",
                args_template={"url": "https://{host.ip}:{port.number}"},
            ),
        },
        expansions=[
            ExpansionRule(
                id="http-enum",
                on_fact="OpenPort{service: http|https}",
                spawn=["web_dir_enum"],
            ),
        ],
    )


def test_matching_fact_spawns_requested_task_types():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    host = Host.new(ip="1.2.3.4")
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    spawns = eng.on_fact(port, known_facts=[host, port])
    assert len(spawns) == 1
    s: SpawnRequest = spawns[0]
    assert s.task_type == "web_dir_enum"
    assert s.rule_id == "http-enum"
    assert s.triggered_by_fact_id == port.id


def test_non_matching_fact_spawns_nothing():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    ssh = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    assert eng.on_fact(ssh, known_facts=[ssh]) == []


def test_spawn_skipped_when_required_consume_missing():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    spawns = eng.on_fact(port, known_facts=[port])
    assert spawns == []


def test_spawn_request_carries_resolved_consume_map():
    pb = _playbook_with_web_rule()
    eng = ExpansionEngine(pb)
    host = Host.new(ip="1.2.3.4")
    port = OpenPort.new(host_ip="1.2.3.4", number=443, service="https")
    [spawn] = eng.on_fact(port, known_facts=[host, port])
    assert spawn.consumes["host"] is host
    assert spawn.consumes["port"] is port
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_expansion.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/scenarios/expansion.py`:

```python
"""Expansion engine: turns a new fact into requests to spawn new tasks."""
from __future__ import annotations

from dataclasses import dataclass, field

from agent_smith.evidence.facts import Fact
from agent_smith.evidence.matcher import Predicate, parse_predicate
from agent_smith.scenarios.playbook import Playbook


@dataclass
class SpawnRequest:
    task_type: str
    rule_id: str
    triggered_by_fact_id: str
    consumes: dict[str, Fact] = field(default_factory=dict)


class ExpansionEngine:
    def __init__(self, playbook: Playbook) -> None:
        self.playbook = playbook
        self._rule_preds: dict[str, Predicate] = {
            r.id: parse_predicate(r.on_fact)
            for r in playbook.expansions
            if r.on_fact is not None
        }
        self._consume_preds: dict[str, dict[str, Predicate]] = {
            tt.name: {role: parse_predicate(p) for role, p in tt.consumes.items()}
            for tt in playbook.task_types.values()
        }

    def on_fact(self, fact: Fact, known_facts: list[Fact]) -> list[SpawnRequest]:
        out: list[SpawnRequest] = []
        for rule in self.playbook.expansions:
            if rule.on_fact_python is not None:
                continue
            pred = self._rule_preds.get(rule.id)
            if pred is None or not pred.matches(fact):
                continue

            for ttype in rule.spawn:
                consume_preds = self._consume_preds.get(ttype, {})
                resolved = self._resolve_consumes(consume_preds, fact, known_facts)
                if resolved is None:
                    continue
                out.append(SpawnRequest(
                    task_type=ttype,
                    rule_id=rule.id,
                    triggered_by_fact_id=fact.id,
                    consumes=resolved,
                ))
        return out

    @staticmethod
    def _resolve_consumes(
        consume_preds: dict[str, Predicate],
        triggering: Fact,
        known_facts: list[Fact],
    ) -> dict[str, Fact] | None:
        resolved: dict[str, Fact] = {}
        for role, pred in consume_preds.items():
            if pred.matches(triggering):
                resolved[role] = triggering
                continue
            match = next((f for f in known_facts if pred.matches(f)), None)
            if match is None:
                return None
            resolved[role] = match
        return resolved
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/scenarios/test_expansion.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/scenarios/expansion.py tests/v2/scenarios/test_expansion.py
git commit -m "feat(phase1): expansion engine turns facts into SpawnRequests"
```

---

## Task 14: Parser protocol and base

**Files:**
- Create: `src/agent_smith/executor/parsers/base.py`
- Modify: `src/agent_smith/executor/parsers/__init__.py`

- [ ] **Step 1: Write the base module**

Create `src/agent_smith/executor/parsers/base.py`:

```python
"""Parser protocol and shared input types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_smith.evidence.facts import Fact


@dataclass
class ToolRun:
    run_id: str
    tool: str
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    started_at: float
    finished_at: float
    timed_out: bool = False
    artifact_paths: list[str] = field(default_factory=list)


class Parser(Protocol):
    tool: str

    def parse(self, run: ToolRun) -> list[Fact]:
        ...
```

- [ ] **Step 2: Add a parser registry scaffold**

Replace the empty `src/agent_smith/executor/parsers/__init__.py` with:

```python
"""Parser registry for structured tool-output extraction."""
from __future__ import annotations

from agent_smith.executor.parsers.base import Parser, ToolRun

_REGISTRY: dict[str, Parser] = {}


def register(parser: Parser) -> None:
    _REGISTRY[parser.tool] = parser


def get_parser(tool: str) -> Parser | None:
    return _REGISTRY.get(tool)


def reset_for_tests() -> None:
    _REGISTRY.clear()


__all__ = ["Parser", "ToolRun", "register", "get_parser", "reset_for_tests"]
```

- [ ] **Step 3: Commit**

```bash
git add src/agent_smith/executor/parsers/base.py src/agent_smith/executor/parsers/__init__.py
git commit -m "feat(phase1): Parser protocol + registry"
```

---

## Task 15: Nmap parser

**Files:**
- Create: `src/agent_smith/executor/parsers/nmap_parser.py`
- Modify: `src/agent_smith/executor/parsers/__init__.py` (register nmap)
- Test: `tests/v2/executor/parsers/test_nmap_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/executor/parsers/test_nmap_parser.py`:

```python
"""Tests for the nmap XML parser."""
from __future__ import annotations

from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.parsers.nmap_parser import NmapXmlParser


_XML_SIMPLE = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <hostnames><hostname name="target.example"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.25.3"/>
      </port>
      <port protocol="tcp" portid="3389">
        <state state="filtered"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


def _run(stdout: str) -> ToolRun:
    return ToolRun(
        run_id="r1",
        tool="nmap",
        command="nmap -sV -oX - 203.0.113.10",
        stdout=stdout,
        stderr="",
        exit_code=0,
        duration_ms=1000,
        started_at=0.0,
        finished_at=1.0,
    )


def test_emits_host_and_open_ports():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    kinds = [f.type for f in facts]
    assert kinds.count("Host") == 1
    assert kinds.count("OpenPort") == 2
    host = next(f for f in facts if f.type == "Host")
    assert host.payload["ip"] == "203.0.113.10"
    assert host.payload["hostname"] == "target.example"
    assert host.payload["alive"] is True

    ports = {f.payload["number"]: f for f in facts if f.type == "OpenPort"}
    assert set(ports) == {22, 80}
    assert ports[22].payload["service"] == "ssh"
    assert ports[22].payload["version"] == "OpenSSH 8.9"
    assert ports[80].payload["service"] == "http"


def test_skips_non_open_ports():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    assert all(f.payload.get("number") != 3389 for f in facts if f.type == "OpenPort")


def test_marks_provenance_on_emitted_facts():
    facts = NmapXmlParser().parse(_run(_XML_SIMPLE))
    for f in facts:
        assert len(f.provenance) == 1
        prov = f.provenance[0]
        assert prov.parser == "nmap"
        assert prov.tool_run_id == "r1"


def test_handles_garbage_input_gracefully():
    facts = NmapXmlParser().parse(_run("not xml at all"))
    assert facts == []
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/executor/parsers/test_nmap_parser.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/executor/parsers/nmap_parser.py`:

```python
"""Nmap XML parser: emits Host and OpenPort facts."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from agent_smith.evidence.facts import Fact, Host, OpenPort, Provenance
from agent_smith.executor.parsers.base import ToolRun

logger = logging.getLogger(__name__)


class NmapXmlParser:
    tool = "nmap"

    def parse(self, run: ToolRun) -> list[Fact]:
        facts: list[Fact] = []
        try:
            root = ET.fromstring(run.stdout)
        except ET.ParseError as e:
            logger.warning("nmap parser: XML parse failed: %s", e)
            return []

        for host_el in root.findall("host"):
            ip = _first_ipv4(host_el)
            if ip is None:
                continue
            status = host_el.find("status")
            alive = status is not None and status.get("state") == "up"
            hostname_el = host_el.find("hostnames/hostname")
            hostname = hostname_el.get("name") if hostname_el is not None else None

            host_fact = Host.new(ip=ip, hostname=hostname, alive=alive)
            host_fact.append_provenance(
                Provenance(
                    task_id="", tool_run_id=run.run_id, parser=self.tool,
                    timestamp=run.finished_at, snippet=f"host {ip}",
                )
            )
            facts.append(host_fact)

            for port_el in host_el.findall("ports/port"):
                state_el = port_el.find("state")
                if state_el is None or state_el.get("state") != "open":
                    continue
                try:
                    number = int(port_el.get("portid"))
                except (TypeError, ValueError):
                    continue
                protocol = port_el.get("protocol", "tcp")
                svc_el = port_el.find("service")
                service = svc_el.get("name") if svc_el is not None else None
                version_parts: list[str] = []
                if svc_el is not None:
                    if svc_el.get("product"):
                        version_parts.append(svc_el.get("product"))
                    if svc_el.get("version"):
                        version_parts.append(svc_el.get("version"))
                version = " ".join(version_parts) or None

                p = OpenPort.new(
                    host_ip=ip, number=number, protocol=protocol,
                    service=service, version=version,
                )
                p.append_provenance(
                    Provenance(
                        task_id="", tool_run_id=run.run_id, parser=self.tool,
                        timestamp=run.finished_at,
                        snippet=f"{number}/{protocol} {service or ''}".strip(),
                    )
                )
                facts.append(p)
        return facts


def _first_ipv4(host_el: ET.Element) -> str | None:
    for addr in host_el.findall("address"):
        if addr.get("addrtype") == "ipv4":
            return addr.get("addr")
    return None
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/executor/parsers/test_nmap_parser.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Register the parser**

Replace `src/agent_smith/executor/parsers/__init__.py`:

```python
"""Parser registry for structured tool-output extraction."""
from __future__ import annotations

from agent_smith.executor.parsers.base import Parser, ToolRun

_REGISTRY: dict[str, Parser] = {}


def register(parser: Parser) -> None:
    _REGISTRY[parser.tool] = parser


def get_parser(tool: str) -> Parser | None:
    return _REGISTRY.get(tool)


def reset_for_tests() -> None:
    _REGISTRY.clear()
    _register_builtins()


def _register_builtins() -> None:
    from agent_smith.executor.parsers.nmap_parser import NmapXmlParser
    register(NmapXmlParser())


_register_builtins()


__all__ = ["Parser", "ToolRun", "register", "get_parser", "reset_for_tests"]
```

- [ ] **Step 6: Commit**

```bash
git add src/agent_smith/executor/parsers/nmap_parser.py src/agent_smith/executor/parsers/__init__.py tests/v2/executor/parsers/test_nmap_parser.py
git commit -m "feat(phase1): nmap XML parser emits Host/OpenPort, registered"
```

---

## Task 16: Executor shell module

**Files:**
- Create: `src/agent_smith/executor/shell.py`
- Test: `tests/v2/executor/test_shell.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/executor/test_shell.py`:

```python
"""Tests for the shell runner wrapper."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_smith.executor.shell import ShellRunner
from agent_smith.transport.ssh import CommandResult


@dataclass
class FakeSSH:
    next_result: CommandResult
    last_cmd: str = ""
    last_timeout: int = 0

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_cmd = cmd
        self.last_timeout = timeout
        return self.next_result


@pytest.mark.asyncio
async def test_shell_runner_invokes_ssh_and_returns_toolrun():
    ssh = FakeSSH(next_result=CommandResult(
        command="echo hi", stdout="hi\n", stderr="", exit_code=0,
    ))
    runner = ShellRunner(ssh=ssh)
    run = await runner.run(tool="echo", command="echo hi", timeout=10)
    assert run.tool == "echo"
    assert run.command == "echo hi"
    assert run.stdout == "hi\n"
    assert run.exit_code == 0
    assert run.duration_ms >= 0
    assert run.timed_out is False
    assert ssh.last_cmd == "echo hi"
    assert ssh.last_timeout == 10


@pytest.mark.asyncio
async def test_shell_runner_preserves_timeout_flag():
    ssh = FakeSSH(next_result=CommandResult(
        command="sleep 100", stdout="", stderr="timed out", exit_code=None, timed_out=True,
    ))
    runner = ShellRunner(ssh=ssh)
    run = await runner.run(tool="sleep", command="sleep 100", timeout=1)
    assert run.timed_out is True
    assert run.exit_code is None


@pytest.mark.asyncio
async def test_shell_runner_generates_unique_run_ids():
    ssh = FakeSSH(next_result=CommandResult(
        command="x", stdout="", stderr="", exit_code=0,
    ))
    runner = ShellRunner(ssh=ssh)
    r1 = await runner.run(tool="x", command="x")
    r2 = await runner.run(tool="x", command="x")
    assert r1.run_id != r2.run_id
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/executor/test_shell.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/executor/shell.py`:

```python
"""Thin wrapper around SSHConnection producing a ToolRun."""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from agent_smith.executor.parsers.base import ToolRun


class _SshLike(Protocol):
    async def run_command(self, cmd: str, timeout: int = 60): ...


class ShellRunner:
    def __init__(self, ssh: _SshLike) -> None:
        self.ssh = ssh

    async def run(self, tool: str, command: str, timeout: int = 60) -> ToolRun:
        run_id = str(uuid.uuid4())
        started_at = time.time()
        result = await self.ssh.run_command(command, timeout=timeout)
        finished_at = time.time()
        return ToolRun(
            run_id=run_id,
            tool=tool,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=int((finished_at - started_at) * 1000),
            started_at=started_at,
            finished_at=finished_at,
            timed_out=result.timed_out,
        )
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/executor/test_shell.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/executor/shell.py tests/v2/executor/test_shell.py
git commit -m "feat(phase1): ShellRunner wraps SSHConnection into ToolRun"
```

---

## Task 17: Executor (dispatch + args rendering + parser routing)

**Files:**
- Create: `src/agent_smith/executor/executor.py`
- Test: `tests/v2/executor/test_executor.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/executor/test_executor.py`:

```python
"""Tests for the Executor."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_smith.executor.executor import Executor
from agent_smith.graph.task import Task, TaskState
from agent_smith.scenarios.playbook import TaskTypeSpec
from agent_smith.transport.ssh import CommandResult


@dataclass
class FakeSSH:
    stdout: str = ""
    last_cmd: str = ""

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_cmd = cmd
        return CommandResult(command=cmd, stdout=self.stdout, stderr="", exit_code=0)


def _nmap_builder(spec, args):
    return f"nmap -sV -oX - {args['target']}"


@pytest.fixture
def port_scan_spec() -> TaskTypeSpec:
    return TaskTypeSpec(
        name="port_scan",
        consumes={},
        produces=["Host", "OpenPort"],
        tool="nmap",
        args_template={"target": "{target}"},
        parser="nmap",
        timeout=60,
    )


@pytest.mark.asyncio
async def test_executor_resolves_template_args(port_scan_spec, tmp_path: Path):
    ssh = FakeSSH(stdout="<?xml version='1.0'?><nmaprun/>")
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    assert "203.0.113.10" in ssh.last_cmd
    assert result.tool_run.exit_code == 0


@pytest.mark.asyncio
async def test_executor_runs_parser_when_registered(port_scan_spec, tmp_path: Path):
    nmap_xml = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/><address addr="203.0.113.10" addrtype="ipv4"/><ports>
<port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
</ports></host></nmaprun>"""
    ssh = FakeSSH(stdout=nmap_xml)
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    kinds = {f.type for f in result.facts}
    assert "Host" in kinds
    assert "OpenPort" in kinds


@pytest.mark.asyncio
async def test_executor_writes_stdout_file(port_scan_spec, tmp_path: Path):
    ssh = FakeSSH(stdout="<?xml version='1.0'?><nmaprun/>")
    ex = Executor(ssh=ssh, run_dir=tmp_path, command_builder=_nmap_builder)
    task = Task(
        id="t1", task_type="port_scan",
        args={"target": "203.0.113.10"},
        consumes={}, produces=["Host", "OpenPort"],
    )
    task.transition(TaskState.READY)
    task.transition(TaskState.RUNNING)
    result = await ex.run(task, port_scan_spec)
    stdout_file = tmp_path / "tool_runs" / f"{result.tool_run.run_id}.stdout"
    assert stdout_file.exists()
    assert "nmaprun" in stdout_file.read_text()
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/executor/test_executor.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/executor/executor.py`:

```python
"""Executor: dispatches a Task.

Responsibilities:
  1. Build the command from the TaskTypeSpec's args_template + task.args.
  2. Run via ShellRunner.
  3. Persist stdout/stderr to disk (run_dir/tool_runs/{run_id}.{stdout,stderr}).
  4. Route the resulting ToolRun through the registered parser, if any.
  5. Return a TaskExecutionResult with the ToolRun and emitted facts.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_smith.evidence.facts import Fact
from agent_smith.executor.parsers import get_parser
from agent_smith.executor.parsers.base import ToolRun
from agent_smith.executor.shell import ShellRunner
from agent_smith.graph.task import Task
from agent_smith.scenarios.playbook import TaskTypeSpec


class _SshLike(Protocol):
    async def run_command(self, cmd: str, timeout: int = 60): ...


@dataclass
class TaskExecutionResult:
    tool_run: ToolRun
    facts: list[Fact]


CommandBuilder = Callable[[TaskTypeSpec, dict[str, Any]], str]


def default_command_builder(spec: TaskTypeSpec, args: dict[str, Any]) -> str:
    parts: list[str] = [spec.tool]
    for key, template in spec.args_template.items():
        if isinstance(template, str):
            rendered = template.format(**args)
        else:
            rendered = str(template)
        parts.append(f"--{key}={rendered}")
    return " ".join(parts)


class Executor:
    def __init__(
        self,
        ssh: _SshLike,
        run_dir: Path,
        command_builder: CommandBuilder = default_command_builder,
    ) -> None:
        self.runner = ShellRunner(ssh)
        self.run_dir = run_dir
        self.tool_runs_dir = run_dir / "tool_runs"
        self.tool_runs_dir.mkdir(parents=True, exist_ok=True)
        self.command_builder = command_builder

    async def run(self, task: Task, spec: TaskTypeSpec) -> TaskExecutionResult:
        command = self.command_builder(spec, task.args)
        tool_run = await self.runner.run(tool=spec.tool, command=command, timeout=spec.timeout)
        self._persist(tool_run)
        facts: list[Fact] = []
        if spec.parser:
            parser = get_parser(spec.parser)
            if parser is not None:
                facts = parser.parse(tool_run)
                for f in facts:
                    for prov in f.provenance:
                        if prov.task_id == "":
                            prov.task_id = task.id
        return TaskExecutionResult(tool_run=tool_run, facts=facts)

    def _persist(self, run: ToolRun) -> None:
        (self.tool_runs_dir / f"{run.run_id}.stdout").write_text(run.stdout)
        (self.tool_runs_dir / f"{run.run_id}.stderr").write_text(run.stderr)
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/executor/test_executor.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/executor/executor.py tests/v2/executor/test_executor.py
git commit -m "feat(phase1): Executor dispatches task, persists output, routes to parser"
```

---

## Task 18: Mission controller

**Files:**
- Create: `src/agent_smith/controller.py`
- Test: `tests/v2/test_controller.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/v2/test_controller.py`:

```python
"""Tests for MissionController: ties everything together for a single mission."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.types import Event, EventType
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import CommandResult


_NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
      <port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port>
    </ports>
  </host>
</nmaprun>
"""


@dataclass
class FakeSSH:
    script: dict[str, str] = field(default_factory=dict)

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        for keyword, stdout in self.script.items():
            if keyword in cmd:
                return CommandResult(command=cmd, stdout=stdout, stderr="", exit_code=0)
        return CommandResult(command=cmd, stdout="", stderr="no script match", exit_code=1)


def _builder(spec, args):
    if spec.tool == "nmap":
        return f"nmap -sV -oX - {args['target']}"
    if spec.tool == "true":
        return "true"
    return spec.tool


@pytest.fixture
def minimal_playbook_path(tmp_path: Path) -> Path:
    path = tmp_path / "p.yaml"
    path.write_text("""
name: phase1-smoke
version: "1.0"
root_tasks:
  - port_scan:
      target: "203.0.113.10"
task_types:
  port_scan:
    consumes: {}
    produces: [Host, OpenPort]
    tool: nmap
    args_template:
      target: "{target}"
    parser: nmap
  web_probe:
    consumes:
      host: Host
      port: "OpenPort{service: http|https}"
    produces: []
    tool: "true"
    args_template:
      url: "http://{host.ip}:{port.number}"
expansions:
  - id: http-probe
    on_fact: "OpenPort{service: http|https}"
    spawn: [web_probe]
terminations: [scope_exhausted]
""")
    return path


@pytest.mark.asyncio
async def test_mission_runs_root_then_expands(minimal_playbook_path, tmp_path: Path):
    ssh = FakeSSH(script={"nmap": _NMAP_XML, "true": ""})
    bus = EventBus()
    events: list[Event] = []

    async def collect(e: Event) -> None:
        events.append(e)

    bus.subscribe(collect)
    pb = load_playbook(minimal_playbook_path)

    controller = MissionController(
        mission_id="m1",
        playbook=pb,
        ssh=ssh,
        run_dir=tmp_path / "run",
        bus=bus,
        command_builder=_builder,
    )
    await controller.run()

    types = [e.event_type for e in events]
    assert EventType.MISSION_STARTED in types
    assert EventType.TASK_COMPLETE in types
    assert EventType.EXPANSION_FIRED in types
    probe_events = [
        e for e in events
        if e.event_type == EventType.TASK_RUNNING
        and e.payload.get("task_type") == "web_probe"
    ]
    assert len(probe_events) == 1  # only port 80 is http; ssh doesn't match


@pytest.mark.asyncio
async def test_mission_emits_completion_event(minimal_playbook_path, tmp_path: Path):
    ssh = FakeSSH(script={"nmap": _NMAP_XML, "true": ""})
    bus = EventBus()
    seen: list[Event] = []

    async def collect(e: Event) -> None:
        seen.append(e)

    bus.subscribe(collect, event_type=EventType.MISSION_COMPLETE)
    pb = load_playbook(minimal_playbook_path)
    controller = MissionController(
        mission_id="m1", playbook=pb, ssh=ssh, run_dir=tmp_path / "run",
        bus=bus, command_builder=_builder,
    )
    await controller.run()
    assert len(seen) == 1
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/test_controller.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `src/agent_smith/controller.py`:

```python
"""MissionController: runs a single mission end-to-end for Phase 1."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol

from agent_smith.event_stream.bus import EventBus
from agent_smith.event_stream.persistence import JsonlEventPersister
from agent_smith.event_stream.types import Event, EventType
from agent_smith.evidence.facts import Fact
from agent_smith.evidence.store import EvidenceStore
from agent_smith.executor.executor import Executor, default_command_builder, CommandBuilder
from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.graph.scheduler import Scheduler
from agent_smith.graph.task import Task, TaskState
from agent_smith.scenarios.expansion import ExpansionEngine, SpawnRequest
from agent_smith.scenarios.playbook import Playbook


class _SshLike(Protocol):
    async def run_command(self, cmd: str, timeout: int = 60): ...


class MissionController:
    def __init__(
        self,
        mission_id: str,
        playbook: Playbook,
        ssh: _SshLike,
        run_dir: Path,
        bus: EventBus,
        command_builder: CommandBuilder = default_command_builder,
    ) -> None:
        self.mission_id = mission_id
        self.playbook = playbook
        self.bus = bus
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.graph = MissionGraph(mission_id=mission_id)
        self.scheduler = Scheduler(self.graph)
        self.evidence = EvidenceStore()
        self.expansion = ExpansionEngine(playbook)
        self.executor = Executor(ssh=ssh, run_dir=run_dir, command_builder=command_builder)

        self.persister = JsonlEventPersister(run_dir=run_dir)
        self.persister.attach(bus)
        self._seq = 0

    async def run(self) -> None:
        await self.bus.publish(Event(
            event_type=EventType.MISSION_STARTED,
            mission_id=self.mission_id,
            payload={"playbook": self.playbook.name, "version": self.playbook.version},
        ))
        await self.bus.publish(Event(
            event_type=EventType.SCENARIO_LOADED,
            mission_id=self.mission_id,
            payload={"name": self.playbook.name},
        ))

        self._materialize_roots()

        while self.scheduler.has_outstanding_work():
            task = self.scheduler.next_ready()
            if task is None:
                break
            await self._run_task(task)

        await self.bus.publish(Event(
            event_type=EventType.MISSION_COMPLETE,
            mission_id=self.mission_id,
            payload={"tasks_total": self.graph.total(), "tasks_finished": self.graph.finished()},
        ))

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _materialize_roots(self) -> None:
        for root in self.playbook.root_tasks:
            task_id = f"{root.task_type}#{self._next_seq()}"
            t = Task(
                id=task_id,
                task_type=root.task_type,
                args=dict(root.args),
                consumes={},
                produces=list(self.playbook.task_types[root.task_type].produces),
            )
            self.graph.add_task(t)
            t.transition(TaskState.READY)

    async def _run_task(self, task: Task) -> None:
        spec = self.playbook.task_types[task.task_type]
        task.transition(TaskState.RUNNING)
        await self.bus.publish(Event(
            event_type=EventType.TASK_RUNNING,
            mission_id=self.mission_id,
            task_id=task.id,
            payload={"task_type": task.task_type, "args": task.args, "tool": spec.tool},
        ))
        await self.bus.publish(Event(
            event_type=EventType.TOOL_RUN_STARTED,
            mission_id=self.mission_id,
            task_id=task.id,
            payload={"tool": spec.tool},
        ))
        try:
            result = await self.executor.run(task, spec)
        except Exception as exc:
            task.transition(TaskState.FAILED)
            await self.bus.publish(Event(
                event_type=EventType.TASK_FAILED,
                mission_id=self.mission_id,
                task_id=task.id,
                payload={"error": str(exc)},
            ))
            return

        await self.bus.publish(Event(
            event_type=EventType.TOOL_RUN_COMPLETE,
            mission_id=self.mission_id,
            task_id=task.id,
            payload={
                "exit_code": result.tool_run.exit_code,
                "duration_ms": result.tool_run.duration_ms,
                "run_id": result.tool_run.run_id,
            },
        ))

        for fact in result.facts:
            insert_result = self.evidence.insert(fact)
            await self.bus.publish(Event(
                event_type=(
                    EventType.FACT_EMITTED if insert_result.inserted else EventType.FACT_UPDATED
                ),
                mission_id=self.mission_id,
                task_id=task.id,
                payload={
                    "fact_id": insert_result.fact.id,
                    "type": insert_result.fact.type,
                    "key": insert_result.fact.canonical_key,
                },
            ))
            await self._fire_expansions(insert_result.fact, parent_task_id=task.id)

        task.transition(TaskState.COMPLETE)
        await self.bus.publish(Event(
            event_type=EventType.TASK_COMPLETE,
            mission_id=self.mission_id,
            task_id=task.id,
            payload={"facts_emitted": len(result.facts)},
        ))

    async def _fire_expansions(self, fact: Fact, parent_task_id: str) -> None:
        known = self.evidence.all()
        for spawn in self.expansion.on_fact(fact, known):
            spawn_task = self._materialize_spawn(spawn, parent_task_id)
            await self.bus.publish(Event(
                event_type=EventType.EXPANSION_FIRED,
                mission_id=self.mission_id,
                task_id=spawn_task.id,
                payload={
                    "rule_id": spawn.rule_id,
                    "triggered_by_fact_id": spawn.triggered_by_fact_id,
                    "task_type": spawn.task_type,
                },
            ))
            await self.bus.publish(Event(
                event_type=EventType.TASK_CREATED,
                mission_id=self.mission_id,
                task_id=spawn_task.id,
                payload={"task_type": spawn_task.task_type, "parent_task_id": parent_task_id},
            ))
            spawn_task.transition(TaskState.READY)
            await self.bus.publish(Event(
                event_type=EventType.TASK_READY,
                mission_id=self.mission_id,
                task_id=spawn_task.id,
                payload={},
            ))

    def _materialize_spawn(self, spawn: SpawnRequest, parent_task_id: str) -> Task:
        spec = self.playbook.task_types[spawn.task_type]
        args = self._render_args(spec.args_template, spawn.consumes)
        tid = f"{spawn.task_type}#{self._next_seq()}"
        t = Task(
            id=tid,
            task_type=spawn.task_type,
            args=args,
            consumes=dict(spawn.consumes),
            produces=list(spec.produces),
            triggered_by_rule=spawn.rule_id,
            triggered_by_fact_ids=[spawn.triggered_by_fact_id],
            parent_task_id=parent_task_id,
        )
        self.graph.add_task(t)
        return t

    @staticmethod
    def _render_args(template: dict[str, Any], consumes: dict[str, Fact]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in template.items():
            if isinstance(value, str):
                resolved[key] = _render_string(value, consumes)
            else:
                resolved[key] = value
        return resolved


_RENDER_PATTERN = re.compile(r"\{(\w+)\.(\w+)\}")


def _render_string(template: str, consumes: dict[str, Fact]) -> str:
    def replace(m: re.Match[str]) -> str:
        role, field_ = m.group(1), m.group(2)
        fact = consumes.get(role)
        if fact is None:
            return m.group(0)
        return str(fact.payload.get(field_, m.group(0)))

    return _RENDER_PATTERN.sub(replace, template)
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/test_controller.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/controller.py tests/v2/test_controller.py
git commit -m "feat(phase1): MissionController wires graph+evidence+expansion+executor"
```

---

## Task 19: Skeleton playbook YAML

**Files:**
- Create: `src/agent_smith/playbooks/skeleton_portscan.yaml`

- [ ] **Step 1: Write the playbook**

Create `src/agent_smith/playbooks/skeleton_portscan.yaml`:

```yaml
# Phase 1 demo playbook.
# Runs a port scan, then runs a no-op "web_probe" task per http/https port
# to demonstrate expansion rules firing end-to-end.
name: skeleton-portscan
version: "1.0"
scope_required: false
allowed_risks: [low, medium]

root_tasks:
  - port_scan:
      target: "${TARGET}"

task_types:
  port_scan:
    consumes: {}
    produces: [Host, OpenPort]
    tool: nmap
    args_template:
      target: "{target}"
    parser: nmap
    timeout: 300

  web_probe:
    consumes:
      host: Host
      port: "OpenPort{service: http|https}"
    produces: []
    tool: curl
    args_template:
      url: "http://{host.ip}:{port.number}"
    timeout: 30

expansions:
  - id: http-probe
    on_fact: "OpenPort{service: http|https}"
    spawn: [web_probe]

terminations:
  - scope_exhausted
```

- [ ] **Step 2: Commit**

```bash
git add src/agent_smith/playbooks/skeleton_portscan.yaml
git commit -m "feat(phase1): skeleton portscan demo playbook"
```

---

## Task 20: v2 API routes (assessments)

**Files:**
- Create: `src/agent_smith/server/v2_routes.py`
- Modify: `src/agent_smith/server/app.py` (mount the router)
- Test: `tests/v2/test_routes.py`

- [ ] **Step 1: Inspect existing server structure**

```bash
PYTHONPATH=src python -c "from agent_smith.server.app import create_app; print(create_app)"
```

Expected: prints a function reference. Then read `src/agent_smith/server/app.py` to identify where v1 routers are mounted — you'll add the v2 router in the same place.

- [ ] **Step 2: Write the failing tests**

Create `tests/v2/test_routes.py`:

```python
"""Tests for the /api/v2 HTTP surface."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_smith.server.v2_routes import AssessmentStore, router


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    AssessmentStore.reset(base_dir=tmp_path / "runs")
    app = FastAPI()
    app.include_router(router)
    return app


def test_create_assessment_returns_id_and_status(app):
    client = TestClient(app)
    resp = client.post("/api/v2/assessments", json={
        "playbook": "skeleton-portscan",
        "target": "203.0.113.10",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["mission_id"]
    assert body["status"] == "created"
    assert body["playbook"] == "skeleton-portscan"


def test_list_assessments_returns_created(app):
    client = TestClient(app)
    client.post("/api/v2/assessments", json={"playbook": "skeleton-portscan", "target": "1.2.3.4"})
    client.post("/api/v2/assessments", json={"playbook": "skeleton-portscan", "target": "5.6.7.8"})
    resp = client.get("/api/v2/assessments")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


def test_get_assessment_graph_empty_before_run(app):
    client = TestClient(app)
    created = client.post("/api/v2/assessments", json={
        "playbook": "skeleton-portscan", "target": "1.2.3.4",
    }).json()
    resp = client.get(f"/api/v2/assessments/{created['mission_id']}/graph")
    assert resp.status_code == 200
    g = resp.json()
    assert g["mission_id"] == created["mission_id"]
    assert g["total"] == 0


def test_get_unknown_assessment_returns_404(app):
    client = TestClient(app)
    resp = client.get("/api/v2/assessments/nope/graph")
    assert resp.status_code == 404
```

- [ ] **Step 3: Run the tests to confirm they fail**

```bash
PYTHONPATH=src pytest tests/v2/test_routes.py -v
```

Expected: `ModuleNotFoundError: agent_smith.server.v2_routes`.

- [ ] **Step 4: Write the implementation**

Create `src/agent_smith/server/v2_routes.py`:

```python
"""Phase 1 HTTP surface for the v2 engine.

Creates and lists assessments, exposes the mission graph as JSON. Execution
via HTTP lands in Phase 4; for Phase 1 the integration test drives the
controller directly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_smith.graph.mission_graph import MissionGraph


router = APIRouter(prefix="/api/v2", tags=["assessments-v2"])


@dataclass
class _AssessmentRecord:
    mission_id: str
    playbook: str
    target: str
    status: str = "created"
    graph: MissionGraph | None = None


class _Store:
    def __init__(self) -> None:
        self.base_dir: Path = Path("data/runs")
        self.records: dict[str, _AssessmentRecord] = {}

    def reset(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.records = {}


AssessmentStore = _Store()


class CreateAssessmentRequest(BaseModel):
    playbook: str
    target: str


class CreateAssessmentResponse(BaseModel):
    mission_id: str
    status: str
    playbook: str
    target: str


class AssessmentSummary(BaseModel):
    mission_id: str
    status: str
    playbook: str
    target: str


@router.post("/assessments", status_code=201, response_model=CreateAssessmentResponse)
async def create_assessment(body: CreateAssessmentRequest) -> CreateAssessmentResponse:
    mission_id = str(uuid.uuid4())
    AssessmentStore.records[mission_id] = _AssessmentRecord(
        mission_id=mission_id,
        playbook=body.playbook,
        target=body.target,
    )
    return CreateAssessmentResponse(
        mission_id=mission_id, status="created",
        playbook=body.playbook, target=body.target,
    )


@router.get("/assessments", response_model=list[AssessmentSummary])
async def list_assessments() -> list[AssessmentSummary]:
    return [
        AssessmentSummary(
            mission_id=r.mission_id, status=r.status,
            playbook=r.playbook, target=r.target,
        )
        for r in AssessmentStore.records.values()
    ]


@router.get("/assessments/{mission_id}/graph")
async def get_graph(mission_id: str) -> dict[str, Any]:
    record = AssessmentStore.records.get(mission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    if record.graph is None:
        return {"mission_id": mission_id, "total": 0, "finished": 0, "tasks": []}
    return record.graph.to_dict()
```

- [ ] **Step 5: Mount the router in the main app**

Read `src/agent_smith/server/app.py`, then add in the same style as existing router mounts:

```python
from agent_smith.server.v2_routes import router as v2_router
# inside create_app():
app.include_router(v2_router)
```

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
PYTHONPATH=src pytest tests/v2/test_routes.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 7: Confirm existing tests still pass**

```bash
PYTHONPATH=src pytest tests/ -x
```

Expected: everything green.

- [ ] **Step 8: Commit**

```bash
git add src/agent_smith/server/v2_routes.py src/agent_smith/server/app.py tests/v2/test_routes.py
git commit -m "feat(phase1): /api/v2 assessments endpoints + graph query"
```

---

## Task 21: End-to-end skeleton integration test

**Files:**
- Create: `tests/v2/integration/test_skeleton_portscan.py`

- [ ] **Step 1: Write the integration test**

Create `tests/v2/integration/test_skeleton_portscan.py`:

```python
"""End-to-end skeleton_portscan playbook run with a mocked SSH transport."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import CommandResult


_NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
      <port protocol="tcp" portid="80"><state state="open"/><service name="http" product="nginx" version="1.25"/></port>
      <port protocol="tcp" portid="443"><state state="open"/><service name="https"/></port>
    </ports>
  </host>
</nmaprun>
"""


@dataclass
class FakeSSH:
    last_commands: list[str] = field(default_factory=list)

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        self.last_commands.append(cmd)
        if "nmap" in cmd:
            return CommandResult(command=cmd, stdout=_NMAP_XML, stderr="", exit_code=0)
        if "curl" in cmd:
            return CommandResult(command=cmd, stdout="<html>ok</html>", stderr="", exit_code=0)
        return CommandResult(command=cmd, stdout="", stderr="unknown cmd", exit_code=1)


@pytest.mark.asyncio
async def test_skeleton_mission_runs_and_events_are_persisted(tmp_path: Path):
    playbook_path = Path("src/agent_smith/playbooks/skeleton_portscan.yaml")
    raw = playbook_path.read_text().replace("${TARGET}", "203.0.113.10")
    staged = tmp_path / "skeleton_portscan.yaml"
    staged.write_text(raw)
    pb = load_playbook(staged)

    def builder(spec, args):
        if spec.tool == "nmap":
            return f"nmap -sV -oX - {args['target']}"
        if spec.tool == "curl":
            return f"curl -sS -o /dev/null -w '%{{http_code}}' {args['url']}"
        return spec.tool

    run_dir = tmp_path / "run"
    ssh = FakeSSH()
    bus = EventBus()
    controller = MissionController(
        mission_id="m1",
        playbook=pb,
        ssh=ssh,
        run_dir=run_dir,
        bus=bus,
        command_builder=builder,
    )
    await controller.run()

    events_path = run_dir / "events.jsonl"
    assert events_path.exists()
    lines = events_path.read_text().strip().splitlines()
    types = [json.loads(line)["event_type"] for line in lines]
    assert "mission_started" in types
    assert "mission_complete" in types
    assert types.count("fact_emitted") >= 4
    assert "expansion_fired" in types

    nmap_cmds = [c for c in ssh.last_commands if "nmap" in c]
    curl_cmds = [c for c in ssh.last_commands if "curl" in c]
    assert len(nmap_cmds) == 1
    assert len(curl_cmds) == 2

    runs_dir = run_dir / "tool_runs"
    stdout_files = list(runs_dir.glob("*.stdout"))
    assert len(stdout_files) == 3
```

- [ ] **Step 2: Run the integration test**

```bash
PYTHONPATH=src pytest tests/v2/integration/test_skeleton_portscan.py -v
```

Expected: PASS. If it fails, the diagnostic will point to a specific earlier module — fix there, not here.

- [ ] **Step 3: Run the full v2 test suite**

```bash
PYTHONPATH=src pytest tests/v2/ -v
```

Expected: every v2 test passes.

- [ ] **Step 4: Run the full test suite to confirm no regressions**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: all tests green.

- [ ] **Step 5: Commit**

```bash
git add tests/v2/integration/test_skeleton_portscan.py
git commit -m "test(phase1): end-to-end skeleton playbook integration test"
```

---

## Task 22: Minimal dashboard wiring (graph JSON view)

**Files:**
- Modify: `src/agent_smith/server/static/index.html` (add v2 section)
- Modify: `src/agent_smith/server/static/app.js` (fetch & render v2 graph using safe DOM APIs)
- Modify: `src/agent_smith/server/static/style.css` (minimal style)

**Security note:** assessment data is user-controlled — never interpolate it into `innerHTML`. The JS below constructs DOM nodes via `createElement` / `textContent` for XSS safety. Do not refactor to `innerHTML`.

- [ ] **Step 1: Add the v2 panel to the dashboard HTML**

Read `src/agent_smith/server/static/index.html` first to match existing layout. Then add near the end of the main content area, before the closing body tag:

```html
<section id="v2-assessments" class="panel">
  <h2>v2 Assessments (Phase 1)</h2>
  <p class="subtle">Read-only; rich UI arrives in Phase 4.</p>
  <div id="v2-list"></div>
  <div id="v2-graph-container">
    <h3>Selected assessment graph</h3>
    <pre id="v2-graph-json">(select an assessment)</pre>
  </div>
</section>
```

- [ ] **Step 2: Wire up the JS (XSS-safe)**

Append to `src/agent_smith/server/static/app.js`:

```javascript
// --- Phase 1: v2 assessments (read-only) ---
async function v2LoadList() {
  const res = await fetch("/api/v2/assessments");
  if (!res.ok) return;
  const items = await res.json();
  const listEl = document.getElementById("v2-list");
  if (!listEl) return;

  // Clear existing children safely
  while (listEl.firstChild) listEl.removeChild(listEl.firstChild);

  if (items.length === 0) {
    const em = document.createElement("em");
    em.textContent = "no v2 assessments yet";
    listEl.appendChild(em);
    return;
  }

  for (const i of items) {
    const btn = document.createElement("button");
    btn.className = "v2-item";
    btn.dataset.id = i.mission_id;
    // textContent prevents any HTML interpretation of user-controlled fields
    btn.textContent = `${i.playbook} → ${i.target} [${i.status}]`;
    btn.addEventListener("click", () => v2LoadGraph(i.mission_id));
    listEl.appendChild(btn);
  }
}

async function v2LoadGraph(missionId) {
  const res = await fetch(`/api/v2/assessments/${encodeURIComponent(missionId)}/graph`);
  const graphEl = document.getElementById("v2-graph-json");
  if (!graphEl) return;
  if (!res.ok) {
    graphEl.textContent = `error: ${res.status}`;
    return;
  }
  const g = await res.json();
  graphEl.textContent = JSON.stringify(g, null, 2);
}

if (document.getElementById("v2-list")) {
  v2LoadList();
  setInterval(v2LoadList, 5000);
}
```

- [ ] **Step 3: Minimal styling**

Append to `src/agent_smith/server/static/style.css`:

```css
#v2-assessments { margin-top: 2em; border-top: 1px solid #333; padding-top: 1em; }
#v2-assessments .panel { padding: 1em; }
#v2-assessments .subtle { opacity: 0.7; font-size: 0.9em; }
#v2-list { display: flex; flex-direction: column; gap: 0.25em; margin-bottom: 1em; }
.v2-item { text-align: left; padding: 0.5em; cursor: pointer; background: #222; color: #ddd; border: 1px solid #333; }
.v2-item:hover { background: #333; }
#v2-graph-json { max-height: 400px; overflow: auto; background: #111; color: #ddd; padding: 0.5em; }
```

- [ ] **Step 4: Manually verify the UI renders**

```bash
PYTHONPATH=src uvicorn agent_smith.server.app:create_app --factory --reload --port 8080
```

In another terminal:

```bash
curl -s -X POST http://localhost:8080/api/v2/assessments \
  -H 'content-type: application/json' \
  -d '{"playbook":"skeleton-portscan","target":"203.0.113.10"}'
curl -s http://localhost:8080/api/v2/assessments
```

Open `http://localhost:8080` in a browser (auth seeded per `README.md`). Confirm the "v2 Assessments (Phase 1)" panel appears, lists the created assessment, and clicking it loads an empty-graph JSON blob.

- [ ] **Step 5: Commit**

```bash
git add src/agent_smith/server/static/
git commit -m "feat(phase1): minimal v2 assessments panel in dashboard (XSS-safe)"
```

---

## Task 23: Final v2 suite check and import sanity

**Files:** none — verification only.

- [ ] **Step 1: Full test run**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: every test passes. If anything fails, **stop** and fix before moving on.

- [ ] **Step 2: Quick smoke import check**

```bash
PYTHONPATH=src python -c "
from agent_smith.controller import MissionController
from agent_smith.scenarios.loader import load_playbook
from agent_smith.evidence.store import EvidenceStore
from agent_smith.graph.mission_graph import MissionGraph
from agent_smith.event_stream.types import EventType
from agent_smith.executor.parsers import get_parser
print('nmap parser registered:', get_parser('nmap') is not None)
print('all Phase 1 imports OK')
"
```

Expected: prints `nmap parser registered: True` and `all Phase 1 imports OK`.

- [ ] **Step 3: Confirm no LLM calls were introduced**

```bash
PYTHONPATH=src python -c "
import ast, pathlib
phase1_dirs = ['event_stream', 'evidence', 'graph', 'scenarios', 'executor']
root = pathlib.Path('src/agent_smith')
offenders = []
for d in phase1_dirs:
    for p in (root / d).rglob('*.py'):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name in ('anthropic', 'openai', 'ollama'):
                        offenders.append((str(p), n.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module in ('anthropic', 'openai', 'ollama') or node.module.startswith('agent_smith.llm'):
                    offenders.append((str(p), node.module))
print('offenders:', offenders)
assert not offenders, 'Phase 1 modules must not import LLM providers'
"
```

Expected: `offenders: []` and no assertion error.

- [ ] **Step 4: Skim the commit log**

```bash
git log --oneline main..HEAD 2>/dev/null || git log --oneline -n 30
```

Expected: a clean, readable commit history with one commit per Task N.

---

## Task 24: Update README with Phase 1 demo section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Phase 1 demo section**

Append to `README.md`:

````markdown
## Phase 1 demo (v2 engine skeleton)

The v2 engine runs alongside the existing HTB loop. Phase 1 ships the engine skeleton — DAG graph, typed facts, YAML playbook loader, executor with nmap parser — with no LLM calls.

Run the included skeleton playbook against a host you own:

```bash
PYTHONPATH=src python - <<'PY'
import asyncio, pathlib
from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import SSHConnection

async def main():
    path = pathlib.Path("src/agent_smith/playbooks/skeleton_portscan.yaml")
    staged = pathlib.Path("/tmp/skeleton_portscan.yaml")
    staged.write_text(path.read_text().replace("${TARGET}", "203.0.113.10"))
    pb = load_playbook(staged)

    ssh = SSHConnection(host="YOUR_ATTACK_BOX_IP", user="root", key_path="~/.ssh/id_rsa")
    await ssh.connect()
    try:
        def builder(spec, args):
            if spec.tool == "nmap":
                return f"nmap -sV -oX - {args['target']}"
            if spec.tool == "curl":
                return f"curl -sS -o /dev/null -w '%{{http_code}}' {args['url']}"
            return spec.tool

        bus = EventBus()
        controller = MissionController(
            mission_id="demo-1",
            playbook=pb,
            ssh=ssh,
            run_dir=pathlib.Path("data/runs/demo-1"),
            bus=bus,
            command_builder=builder,
        )
        await controller.run()
    finally:
        await ssh.disconnect()

asyncio.run(main())
PY
```

Artifacts land under `data/runs/demo-1/`:
- `events.jsonl` — complete event stream
- `tool_runs/*.stdout` / `.stderr` — raw tool outputs

The v2 dashboard panel at the bottom of the existing UI shows the assessment list and graph JSON (created assessments only show up if you POST to `/api/v2/assessments`).

**Phase 1 intentionally omits:** LLM calls, scope guard, approval queue, cost meter, mindmap UI. Those land in Phases 2–4.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(phase1): add Phase 1 demo section to README"
```

---

## Final verification checklist

After Task 24, run through these manually:

- [ ] `git log --oneline` shows one commit per Task (≈24 commits on the feature branch).
- [ ] `PYTHONPATH=src pytest tests/ -v` passes end to end.
- [ ] `PYTHONPATH=src pytest tests/v2/ -v` passes.
- [ ] The integration test `tests/v2/integration/test_skeleton_portscan.py` passes.
- [ ] The smoke-check in Task 23 Step 3 reports `offenders: []`.
- [ ] Existing v1 tests under `tests/test_*.py` still pass.
- [ ] Merge to `main` once verified.

---

## What comes next (Phase 2 preview — NOT IN THIS PLAN)

After Phase 1 lands and the skeleton demo is green:

- Three-tier decision router (Tier 0/1/2) with Anthropic prompt caching.
- Cost meter + `tier_call` events + per-tier circuit breakers.
- Scope guard + risk classifier + approval queue (backend; UI is Phase 4).
- Five more structured parsers: feroxbuster, gobuster, nuclei, nikto, crackmapexec.
- Generic Tier 1 fallback parser for unknown tools.
- LRU result cache on executor dispatch.

Each becomes its own task group in the Phase 2 plan, written after Phase 1 ships so it can incorporate whatever we learn here.
