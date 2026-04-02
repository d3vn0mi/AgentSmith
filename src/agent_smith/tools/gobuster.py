"""Gobuster directory/DNS enumeration tool."""

from __future__ import annotations

import re
from typing import Any

from agent_smith.tools.base import Tool, ToolResult
from agent_smith.transport.ssh import SSHConnection


class GobusterTool(Tool):
    """Run gobuster for directory and DNS enumeration."""

    name = "gobuster"
    description = (
        "Run gobuster for web directory enumeration or DNS subdomain bruteforcing. "
        "Useful for discovering hidden web paths, files, and subdomains on the target."
    )

    async def execute(self, ssh: SSHConnection, **kwargs: Any) -> ToolResult:
        target = kwargs.get("target", "")
        mode = kwargs.get("mode", "dir")
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = kwargs.get("extensions", "")
        extra_args = kwargs.get("extra_args", "")

        if not target:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Error: 'target' parameter is required",
            )

        cmd = f"gobuster {mode} -u {target} -w {wordlist} -t 50 --no-error"

        if extensions and mode == "dir":
            cmd += f" -x {extensions}"
        if extra_args:
            cmd += f" {extra_args}"

        result = await ssh.run_command(cmd, timeout=300)

        parsed = self._parse_output(result.stdout, mode) if result.success else {}

        return ToolResult(
            tool_name=self.name,
            success=result.success,
            output=result.output,
            parsed=parsed,
            raw_command_result=result,
        )

    def _parse_output(self, output: str, mode: str) -> dict[str, Any]:
        """Parse gobuster output into structured results."""
        findings = []

        if mode == "dir":
            pattern = re.compile(r"(/\S+)\s+\(Status:\s*(\d+)\)")
            for match in pattern.finditer(output):
                findings.append({
                    "path": match.group(1),
                    "status_code": int(match.group(2)),
                })
        elif mode == "dns":
            pattern = re.compile(r"Found:\s+(\S+)")
            for match in pattern.finditer(output):
                findings.append({"subdomain": match.group(1)})

        return {"findings": findings, "mode": mode}

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target URL (for dir mode) or domain (for dns mode)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["dir", "dns", "vhost"],
                    "description": "Gobuster mode: dir (directory), dns (subdomain), vhost",
                    "default": "dir",
                },
                "wordlist": {
                    "type": "string",
                    "description": "Path to wordlist file on the attack box",
                    "default": "/usr/share/wordlists/dirb/common.txt",
                },
                "extensions": {
                    "type": "string",
                    "description": "File extensions to search for in dir mode (e.g., 'php,html,txt')",
                },
                "extra_args": {
                    "type": "string",
                    "description": "Additional gobuster arguments",
                },
            },
            "required": ["target"],
        }
