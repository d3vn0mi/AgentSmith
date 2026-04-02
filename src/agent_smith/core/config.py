"""Configuration loading with YAML parsing and environment variable substitution."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class LLMConfig(BaseModel):
    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    base_url: str = "http://ollama:11434"


class TargetConfig(BaseModel):
    ip: str = ""


class AttackBoxConfig(BaseModel):
    host: str = ""
    user: str = "root"
    key_path: str = "~/.ssh/id_rsa"
    password: str = ""


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    domain: str = "localhost"


class AuthConfig(BaseModel):
    jwt_secret: str = "change-me"
    access_token_expiry: int = 3600
    refresh_token_expiry: int = 604800
    users_file: str = "data/users.json"


class AgentConfig(BaseModel):
    max_iterations: int = 200
    command_timeout: int = 120
    phase_timeout: int = 1800


class Config(BaseModel):
    llm: LLMConfig = LLMConfig()
    target: TargetConfig = TargetConfig()
    attack_box: AttackBoxConfig = AttackBoxConfig()
    server: ServerConfig = ServerConfig()
    auth: AuthConfig = AuthConfig()
    agent: AgentConfig = AgentConfig()


_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _substitute_env_vars(value: Any) -> Any:
    """Replace ${VAR_NAME} patterns with environment variable values."""
    if isinstance(value, str):
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")
        return _ENV_VAR_PATTERN.sub(replacer, value)
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    return value


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load configuration from YAML file with environment variable substitution."""
    path = Path(path)
    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        raw = _substitute_env_vars(raw)
    else:
        raw = {}
    return Config(**raw)
