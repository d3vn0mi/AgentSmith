"""Tests for LLM provider abstraction."""

from agent_smith.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition
from agent_smith.llm.factory import create_provider
from agent_smith.core.config import LLMConfig

import pytest


def test_llm_response_has_tool_calls():
    resp = LLMResponse(content="thinking", tool_calls=[
        ToolCall(name="shell", arguments={"command": "ls"}, id="1")
    ])
    assert resp.has_tool_calls


def test_llm_response_no_tool_calls():
    resp = LLMResponse(content="just text")
    assert not resp.has_tool_calls


def test_tool_definition():
    defn = ToolDefinition(
        name="test",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
    )
    assert defn.name == "test"


def test_factory_unknown_provider():
    config = LLMConfig(provider="unknown")
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_provider(config)


def test_factory_claude_requires_key():
    config = LLMConfig(provider="claude", api_key="")
    with pytest.raises(ValueError, match="requires api_key"):
        create_provider(config)


def test_factory_openai_requires_key():
    config = LLMConfig(provider="openai", api_key="")
    with pytest.raises(ValueError, match="requires api_key"):
        create_provider(config)


def test_factory_ollama_no_key_needed():
    config = LLMConfig(provider="ollama", base_url="http://localhost:11434", model="llama3.1")
    provider = create_provider(config)
    assert provider.provider_name == "ollama"
