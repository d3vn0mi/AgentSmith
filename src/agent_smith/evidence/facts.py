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
