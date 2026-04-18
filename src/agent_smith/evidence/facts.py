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


class DirPath:
    TYPE = "DirPath"

    @staticmethod
    def new(
        host: str,
        port: int,
        url: str,
        status: int,
        size: int | None = None,
    ) -> Fact:
        return Fact(
            type=DirPath.TYPE,
            payload={"host": host, "port": port, "url": url,
                      "status": status, "size": size},
            canonical_key=f"dir:{url}",
        )


class WebTech:
    TYPE = "WebTech"

    @staticmethod
    def new(
        host: str,
        port: int,
        software: str,
        version: str | None = None,
    ) -> Fact:
        slug = software.lower().replace(" ", "-")
        return Fact(
            type=WebTech.TYPE,
            payload={"host": host, "port": port,
                      "software": software, "version": version},
            canonical_key=f"tech:{host}:{port}:{slug}",
        )


class Vulnerability:
    TYPE = "Vulnerability"

    @staticmethod
    def new(
        subject_id: str,
        name: str,
        severity: str = "unknown",
        exploit_path: str | None = None,
        cve: str | None = None,
    ) -> Fact:
        ident = cve or name
        return Fact(
            type=Vulnerability.TYPE,
            payload={"subject_id": subject_id, "name": name,
                      "severity": severity,
                      "exploit_path": exploit_path, "cve": cve},
            canonical_key=f"vuln:{subject_id}:{ident}",
        )


class KaliSession:
    TYPE = "KaliSession"

    @staticmethod
    def new(
        session_id: str,
        role: str,
        status: str,
        kali_host: str,
        metadata: dict | None = None,
    ) -> Fact:
        return Fact(
            type=KaliSession.TYPE,
            payload={
                "session_id": session_id,
                "role": role,
                "status": status,
                "kali_host": kali_host,
                "metadata": metadata or {},
            },
            canonical_key=f"session:{session_id}",
        )


class Shell:
    TYPE = "Shell"

    @staticmethod
    def new(
        session_id: str,
        target_host: str,
        listener_port: int,
        callback_ip: str,
        target_user: str | None = None,
        interactive: bool = False,
        status: str = "live",
    ) -> Fact:
        return Fact(
            type=Shell.TYPE,
            payload={
                "session_id": session_id,
                "target_host": target_host,
                "listener_port": listener_port,
                "callback_ip": callback_ip,
                "target_user": target_user,
                "interactive": interactive,
                "status": status,
            },
            canonical_key=f"shell:{session_id}",
        )
