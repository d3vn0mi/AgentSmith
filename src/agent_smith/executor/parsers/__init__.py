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
    from agent_smith.executor.parsers.ffuf_parser import FfufParser
    register(FfufParser())
    from agent_smith.executor.parsers.whatweb_parser import WhatwebParser
    register(WhatwebParser())
    from agent_smith.executor.parsers.searchsploit_parser import SearchsploitParser
    register(SearchsploitParser())
    from agent_smith.executor.parsers.kali_session_parser import KaliSessionParser
    register(KaliSessionParser())
    from agent_smith.executor.parsers.listener_parser import ListenerParser
    register(ListenerParser())
    from agent_smith.executor.parsers.session_exec_parser import SessionExecParser
    register(SessionExecParser())
    from agent_smith.executor.parsers.session_kill_parser import SessionKillParser
    register(SessionKillParser())


_register_builtins()


__all__ = ["Parser", "ToolRun", "register", "get_parser", "reset_for_tests"]
