"""Abstract tool interface and tool registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agent_smith.llm.base import ToolDefinition
from agent_smith.transport.ssh import CommandResult, SSHConnection


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_name: str
    success: bool
    output: str
    parsed: dict[str, Any] = field(default_factory=dict)
    raw_command_result: CommandResult | None = None


class Tool(ABC):
    """Base class for all pentesting tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, ssh: SSHConnection, **kwargs: Any) -> ToolResult:
        """Execute the tool on the remote host via SSH."""
        ...

    def get_definition(self) -> ToolDefinition:
        """Return the tool definition for the LLM."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema(),
        )

    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema for the tool's parameters."""
        ...


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_definitions(self) -> list[ToolDefinition]:
        """Get all tool definitions for the LLM."""
        return [tool.get_definition() for tool in self._tools.values()]
