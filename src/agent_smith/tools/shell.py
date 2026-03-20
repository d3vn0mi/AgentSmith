"""Generic shell command execution tool."""

from __future__ import annotations

from typing import Any

from agent_smith.tools.base import Tool, ToolResult
from agent_smith.transport.ssh import SSHConnection


class ShellTool(Tool):
    """Execute arbitrary shell commands on the attack box."""

    name = "shell"
    description = (
        "Execute a shell command on the attack box. Use this for any command "
        "that doesn't have a dedicated tool. The command runs via SSH on the "
        "assessment machine."
    )

    async def execute(self, ssh: SSHConnection, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 60)

        if not command:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Error: 'command' parameter is required",
            )

        result = await ssh.run_command(command, timeout=timeout)

        return ToolResult(
            tool_name=self.name,
            success=result.success,
            output=result.output,
            raw_command_result=result,
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute on the attack box",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds (default: 60)",
                    "default": 60,
                },
            },
            "required": ["command"],
        }
