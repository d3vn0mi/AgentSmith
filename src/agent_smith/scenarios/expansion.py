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
