"""Ollama (local model) LLM provider."""

from __future__ import annotations

import json
from typing import Any

import httpx

from agent_smith.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition


class OllamaProvider(LLMProvider):
    """Ollama local model provider using the /api/chat endpoint."""

    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        formatted_messages = []

        if system:
            formatted_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg["role"] == "tool":
                formatted_messages.append({
                    "role": "tool",
                    "content": msg["content"],
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                formatted_messages.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            }
                        }
                        for tc in msg["tool_calls"]
                    ],
                })
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        content = message.get("content", "")

        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            tool_calls.append(ToolCall(
                name=func.get("name", ""),
                arguments=func.get("arguments", {}),
                id=f"ollama_{func.get('name', '')}",
            ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=data.get("done_reason", ""),
            raw=data,
        )

    async def close(self) -> None:
        await self._client.aclose()
