"""LLM provider factory - creates the right provider from config."""

from __future__ import annotations

from agent_smith.core.config import LLMConfig
from agent_smith.llm.base import LLMProvider
from agent_smith.llm.claude import ClaudeProvider
from agent_smith.llm.ollama import OllamaProvider
from agent_smith.llm.openai_provider import OpenAIProvider


def create_provider(config: LLMConfig) -> LLMProvider:
    """Create an LLM provider from configuration."""
    match config.provider:
        case "claude" | "anthropic":
            if not config.api_key:
                raise ValueError("Claude provider requires api_key (set ANTHROPIC_API_KEY)")
            return ClaudeProvider(api_key=config.api_key, model=config.model)

        case "openai":
            if not config.api_key:
                raise ValueError("OpenAI provider requires api_key (set OPENAI_API_KEY)")
            return OpenAIProvider(api_key=config.api_key, model=config.model)

        case "ollama":
            return OllamaProvider(base_url=config.base_url, model=config.model)

        case _:
            raise ValueError(
                f"Unknown LLM provider: '{config.provider}'. "
                "Supported: claude, openai, ollama"
            )
