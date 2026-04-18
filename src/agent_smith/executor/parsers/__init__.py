"""Parser registry for structured tool-output extraction."""
from __future__ import annotations

from agent_smith.executor.parsers.base import Parser, ToolRun

_REGISTRY: dict[str, Parser] = {}


def register(parser: Parser) -> None:
    _REGISTRY[parser.tool] = parser


def get_parser(tool: str) -> Parser | None:
    return _REGISTRY.get(tool)


def reset_for_tests() -> None:
    _REGISTRY.clear()
    _register_builtins()


def _register_builtins() -> None:
    from agent_smith.executor.parsers.nmap_parser import NmapXmlParser
    register(NmapXmlParser())


_register_builtins()


__all__ = ["Parser", "ToolRun", "register", "get_parser", "reset_for_tests"]
