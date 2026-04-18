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

        await self._materialize_roots()

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

    async def _materialize_roots(self) -> None:
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
            await self.bus.publish(Event(
                event_type=EventType.TASK_CREATED,
                mission_id=self.mission_id,
                task_id=t.id,
                payload={"task_type": t.task_type, "parent_task_id": None},
            ))
            t.transition(TaskState.READY)
            await self.bus.publish(Event(
                event_type=EventType.TASK_READY,
                mission_id=self.mission_id,
                task_id=t.id,
                payload={},
            ))

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
            await self.bus.publish(Event(
                event_type=EventType.TOOL_RUN_COMPLETE,
                mission_id=self.mission_id,
                task_id=task.id,
                payload={"error": str(exc), "failed": True},
            ))
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
            if insert_result.inserted:
                event_type = EventType.FACT_EMITTED
            elif insert_result.superseded:
                event_type = EventType.FACT_SUPERSEDED
            else:
                event_type = EventType.FACT_UPDATED
            await self.bus.publish(Event(
                event_type=event_type,
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
