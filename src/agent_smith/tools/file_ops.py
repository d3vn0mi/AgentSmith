"""File operation tools for reading, searching, and listing files on the target."""

from __future__ import annotations

from typing import Any

from agent_smith.tools.base import Tool, ToolResult
from agent_smith.transport.ssh import SSHConnection


class FileOpsTool(Tool):
    """Read, search, and list files on the remote system."""

    name = "file_ops"
    description = (
        "Perform file operations on the attack box or target: read file contents, "
        "search for files by name or content, list directory contents, and check "
        "file permissions. Useful for finding flags, config files, and sensitive data."
    )

    async def execute(self, ssh: SSHConnection, **kwargs: Any) -> ToolResult:
        operation = kwargs.get("operation", "read")
        path = kwargs.get("path", "")

        if not path and operation != "find":
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="Error: 'path' parameter is required",
            )

        match operation:
            case "read":
                cmd = f"cat '{path}'"
            case "list":
                cmd = f"ls -la '{path}'"
            case "find":
                name = kwargs.get("name", "")
                search_path = path or "/"
                cmd = f"find '{search_path}' -name '{name}' -type f 2>/dev/null | head -50"
            case "search":
                pattern = kwargs.get("pattern", "")
                cmd = f"grep -rn '{pattern}' '{path}' 2>/dev/null | head -50"
            case "permissions":
                cmd = f"stat -c '%a %U %G %n' '{path}'"
            case "exists":
                cmd = f"test -e '{path}' && echo 'EXISTS' || echo 'NOT_FOUND'"
            case _:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    output=f"Unknown operation: {operation}",
                )

        result = await ssh.run_command(cmd, timeout=30)

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
                "operation": {
                    "type": "string",
                    "enum": ["read", "list", "find", "search", "permissions", "exists"],
                    "description": "File operation to perform",
                    "default": "read",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path to operate on",
                },
                "name": {
                    "type": "string",
                    "description": "Filename pattern for 'find' operation (e.g., 'user.txt')",
                },
                "pattern": {
                    "type": "string",
                    "description": "Search pattern for 'search' operation (grep)",
                },
            },
            "required": ["operation"],
        }
