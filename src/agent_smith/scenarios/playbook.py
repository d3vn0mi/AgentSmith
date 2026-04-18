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
