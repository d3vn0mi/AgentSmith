"""Tests for tool definitions and registry."""

from agent_smith.tools.base import ToolRegistry
from agent_smith.tools.shell import ShellTool
from agent_smith.tools.nmap import NmapTool
from agent_smith.tools.gobuster import GobusterTool
from agent_smith.tools.file_ops import FileOpsTool
from agent_smith.tools.exploit import ExploitTool


def test_tool_registry():
    registry = ToolRegistry()
    registry.register(ShellTool())
    registry.register(NmapTool())

    assert registry.get("shell") is not None
    assert registry.get("nmap") is not None
    assert registry.get("nonexistent") is None
    assert len(registry.list_tools()) == 2


def test_all_tools_have_definitions():
    tools = [ShellTool(), NmapTool(), GobusterTool(), FileOpsTool(), ExploitTool()]
    for tool in tools:
        defn = tool.get_definition()
        assert defn.name == tool.name
        assert defn.description
        assert isinstance(defn.parameters, dict)
        assert defn.parameters.get("type") == "object"


def test_get_definitions():
    registry = ToolRegistry()
    registry.register(ShellTool())
    registry.register(NmapTool())
    registry.register(GobusterTool())
    registry.register(FileOpsTool())
    registry.register(ExploitTool())

    definitions = registry.get_definitions()
    assert len(definitions) == 5
    names = {d.name for d in definitions}
    assert names == {"shell", "nmap", "gobuster", "file_ops", "exploit"}


def test_nmap_parse_output():
    nmap = NmapTool()
    output = """\
Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-01 00:00 UTC
Nmap scan report for 10.10.10.1
Host is up (0.050s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.9p1
80/tcp   open  http    Apache httpd 2.4.52
443/tcp  open  https   nginx 1.18.0
8080/tcp open  http    Node.js Express
"""
    parsed = nmap._parse_output(output)
    assert parsed["host_up"] is True
    assert len(parsed["ports"]) == 4
    assert parsed["ports"][0]["port"] == 22
    assert parsed["ports"][0]["service"] == "ssh"
    assert parsed["ports"][1]["port"] == 80
