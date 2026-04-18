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
