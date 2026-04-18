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
