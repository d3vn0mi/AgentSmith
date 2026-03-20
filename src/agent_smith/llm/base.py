"""Abstract LLM provider interface and response types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A tool/function call requested by the LLM."""
    name: str
    arguments: dict[str, Any]
    id: str = ""


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    raw: Any = None  # Provider-specific raw response

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class ToolDefinition:
    """Tool definition in a provider-agnostic format."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send a completion request to the LLM.

        Args:
            messages: Chat messages in [{"role": "user/assistant/tool", "content": "..."}] format.
            tools: Optional list of tools the LLM can call.
            system: Optional system prompt.

        Returns:
            Unified LLMResponse.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up any resources."""
        ...
