"""Nmap scanning tool with output parsing."""

from __future__ import annotations

import re
from typing import Any

from agent_smith.tools.base import Tool, ToolResult
from agent_smith.transport.ssh import SSHConnection


class NmapTool(Tool):
    """Run nmap scans with structured output parsing."""

    name = "nmap"
    description = (
        "Run an nmap scan against a target. Supports various scan types: "
        "quick TCP scan, full port scan, service version detection, script scanning, "
        "and UDP scan. Results are parsed into structured port/service data."
    )

    async def execute(self, ssh: SSHConnection, **kwargs: Any) -> ToolResult:
        target = kwargs.get("target", "")
        scan_type = kwargs.get("scan_type", "quick")
        ports = kwargs.get("ports", "")
        scripts = kwargs.get("scripts", "")
        extra_args = kwargs.get("extra_args", "")

        if not target:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Error: 'target' parameter is required",
            )

        cmd = self._build_command(target, scan_type, ports, scripts, extra_args)
        result = await ssh.run_command(cmd, timeout=300)

        parsed = self._parse_output(result.stdout) if result.success else {}

        return ToolResult(
            tool_name=self.name,
            success=result.success,
            output=result.output,
            parsed=parsed,
            raw_command_result=result,
        )

    def _build_command(
        self,
        target: str,
        scan_type: str,
        ports: str,
        scripts: str,
        extra_args: str,
    ) -> str:
        base = "nmap"

        match scan_type:
            case "quick":
                base += " -sC -sV -T4"
            case "full":
                base += " -sC -sV -p- -T4"
            case "udp":
                base += " -sU -T4"
            case "version":
                base += " -sV -T4"
            case "scripts":
                base += " -sC -T4"
            case "stealth":
                base += " -sS -T2"
            case _:
                base += " -sC -sV -T4"

        if ports:
            base += f" -p {ports}"
        if scripts:
            base += f" --script={scripts}"
        if extra_args:
            base += f" {extra_args}"

        base += f" {target}"
        return base

    def _parse_output(self, output: str) -> dict[str, Any]:
        """Parse nmap output into structured data."""
        ports = []
        port_pattern = re.compile(
            r"(\d+)/(tcp|udp)\s+(open|filtered|closed)\s+(\S+)\s*(.*)"
        )

        for match in port_pattern.finditer(output):
            ports.append({
                "port": int(match.group(1)),
                "protocol": match.group(2),
                "state": match.group(3),
                "service": match.group(4),
                "version": match.group(5).strip(),
            })

        os_match = re.search(r"OS details:\s*(.+)", output)
        host_up = "Host is up" in output

        return {
            "ports": ports,
            "os_detection": os_match.group(1) if os_match else "",
            "host_up": host_up,
        }

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target IP address or hostname to scan",
                },
                "scan_type": {
                    "type": "string",
                    "enum": ["quick", "full", "udp", "version", "scripts", "stealth"],
                    "description": "Type of nmap scan to perform",
                    "default": "quick",
                },
                "ports": {
                    "type": "string",
                    "description": "Specific ports to scan (e.g., '80,443' or '1-1000')",
                },
                "scripts": {
                    "type": "string",
                    "description": "Nmap scripts to run (e.g., 'vuln' or 'http-enum')",
                },
                "extra_args": {
                    "type": "string",
                    "description": "Additional nmap arguments",
                },
            },
            "required": ["target"],
        }
