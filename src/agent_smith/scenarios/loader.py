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
