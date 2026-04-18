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
