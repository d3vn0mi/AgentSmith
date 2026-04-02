"""Anthropic Claude LLM provider."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from agent_smith.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition


class ClaudeProvider(LLMProvider):
    """Claude API provider with tool-use support."""

    provider_name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": self._convert_messages(messages),
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]

        response = await self._client.messages.create(**kwargs)

        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                    id=block.id,
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "",
            raw=response,
        )

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert generic messages to Claude format."""
        converted = []
        for msg in messages:
            role = msg["role"]
            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg["content"],
                    }],
                })
            elif role == "assistant" and msg.get("tool_calls"):
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"],
                    })
                converted.append({"role": "assistant", "content": content})
            else:
                converted.append({"role": role, "content": msg["content"]})
        return converted

    def _convert_tool(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert to Claude's tool format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    async def close(self) -> None:
        await self._client.close()
