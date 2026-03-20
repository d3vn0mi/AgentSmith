"""Evidence store - structured collection of all pentesting findings."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Port:
    number: int
    protocol: str  # tcp/udp
    state: str  # open/filtered/closed
    service: str
    version: str = ""


@dataclass
class Credential:
    username: str
    password: str = ""
    hash: str = ""
    source: str = ""  # Where it was found
    context: str = ""  # What it's for (ssh, web, db, etc.)


@dataclass
class Vulnerability:
    name: str
    service: str
    severity: str = "unknown"  # critical/high/medium/low/info
    description: str = ""
    exploitable: bool = False
    exploit_ref: str = ""  # CVE, exploit-db ID, etc.


@dataclass
class Finding:
    """A single piece of evidence or discovery."""
    category: str  # port, credential, vulnerability, file, note
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source_command: str = ""


class EvidenceStore:
    """Collects and organizes all findings from the pentest."""

    def __init__(self) -> None:
        self.ports: list[Port] = []
        self.credentials: list[Credential] = []
        self.vulnerabilities: list[Vulnerability] = []
        self.flags: dict[str, str] = {}  # {"user": "HTB{...}", "root": "HTB{...}"}
        self.files_of_interest: list[str] = []
        self.notes: list[str] = []
        self.findings: list[Finding] = []

    def add_port(self, port: Port) -> None:
        if not any(p.number == port.number and p.protocol == port.protocol for p in self.ports):
            self.ports.append(port)
            self.findings.append(Finding(
                category="port",
                data={"port": port.number, "protocol": port.protocol, "service": port.service},
            ))

    def add_credential(self, cred: Credential) -> None:
        self.credentials.append(cred)
        self.findings.append(Finding(
            category="credential",
            data={"username": cred.username, "context": cred.context},
        ))

    def add_vulnerability(self, vuln: Vulnerability) -> None:
        self.vulnerabilities.append(vuln)
        self.findings.append(Finding(
            category="vulnerability",
            data={"name": vuln.name, "severity": vuln.severity},
        ))

    def add_flag(self, flag_type: str, value: str) -> None:
        """Record a captured flag. flag_type is 'user' or 'root'."""
        self.flags[flag_type] = value
        self.findings.append(Finding(
            category="flag",
            data={"type": flag_type, "value": value},
        ))

    def add_note(self, note: str, source_command: str = "") -> None:
        self.notes.append(note)
        self.findings.append(Finding(
            category="note",
            data={"note": note},
            source_command=source_command,
        ))

    def add_file(self, path: str) -> None:
        if path not in self.files_of_interest:
            self.files_of_interest.append(path)

    @property
    def has_user_flag(self) -> bool:
        return "user" in self.flags

    @property
    def has_root_flag(self) -> bool:
        return "root" in self.flags

    @property
    def is_complete(self) -> bool:
        return self.has_user_flag and self.has_root_flag

    def summary(self) -> str:
        """Generate a text summary of all evidence for the LLM context."""
        lines = ["=== EVIDENCE SUMMARY ==="]

        if self.ports:
            lines.append(f"\nOpen Ports ({len(self.ports)}):")
            for p in self.ports:
                version_str = f" - {p.version}" if p.version else ""
                lines.append(f"  {p.number}/{p.protocol} {p.state} {p.service}{version_str}")

        if self.credentials:
            lines.append(f"\nCredentials ({len(self.credentials)}):")
            for c in self.credentials:
                pw = c.password if c.password else f"[hash: {c.hash[:20]}...]" if c.hash else "[no password]"
                lines.append(f"  {c.username}:{pw} ({c.context}) from {c.source}")

        if self.vulnerabilities:
            lines.append(f"\nVulnerabilities ({len(self.vulnerabilities)}):")
            for v in self.vulnerabilities:
                lines.append(f"  [{v.severity}] {v.name} on {v.service}")
                if v.exploit_ref:
                    lines.append(f"    Ref: {v.exploit_ref}")

        if self.files_of_interest:
            lines.append(f"\nFiles of Interest ({len(self.files_of_interest)}):")
            for f in self.files_of_interest:
                lines.append(f"  {f}")

        if self.flags:
            lines.append("\nFlags Captured:")
            for flag_type, value in self.flags.items():
                lines.append(f"  {flag_type}: {value}")

        if self.notes:
            lines.append(f"\nNotes ({len(self.notes)}):")
            for n in self.notes[-10:]:  # Last 10 notes
                lines.append(f"  - {n}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence for API responses."""
        return {
            "ports": [
                {"number": p.number, "protocol": p.protocol, "state": p.state,
                 "service": p.service, "version": p.version}
                for p in self.ports
            ],
            "credentials": [
                {"username": c.username, "context": c.context, "source": c.source,
                 "has_password": bool(c.password), "has_hash": bool(c.hash)}
                for c in self.credentials
            ],
            "vulnerabilities": [
                {"name": v.name, "service": v.service, "severity": v.severity,
                 "exploitable": v.exploitable, "exploit_ref": v.exploit_ref}
                for v in self.vulnerabilities
            ],
            "flags": self.flags,
            "files_of_interest": self.files_of_interest,
            "notes": self.notes[-20:],
        }
