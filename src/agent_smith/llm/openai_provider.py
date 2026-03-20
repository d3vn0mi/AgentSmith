"""OpenAI LLM provider."""

from __future__ import annotations

import json
from typing import Any

import openai

from agent_smith.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition


class OpenAIProvider(LLMProvider):
    """OpenAI API provider with function calling support."""

    provider_name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.model = model
        self._client = openai.AsyncOpenAI(api_key=api_key)

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
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": msg["content"],
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                formatted_messages.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in msg["tool_calls"]
                    ],
                })
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }

        if tools:
            kwargs["tools"] = [
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

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                    id=tc.id,
                ))

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "",
            raw=response,
        )

    async def close(self) -> None:
        await self._client.close()
