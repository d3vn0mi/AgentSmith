"""Tests for the YAML playbook loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_smith.scenarios.loader import PlaybookValidationError, load_playbook


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def test_load_minimal_playbook(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: minimal
version: "1.0"
root_tasks:
  - port_scan:
      host_set: ["1.2.3.4"]
task_types:
  port_scan:
    consumes: {}
    produces: [Host, OpenPort]
    tool: nmap
    args_template:
      target: "{host}"
    parser: nmap
expansions: []
terminations:
  - scope_exhausted
""")
    pb = load_playbook(path)
    assert pb.name == "minimal"
    assert pb.root_tasks[0].task_type == "port_scan"
    assert pb.root_tasks[0].args == {"host_set": ["1.2.3.4"]}
    assert "port_scan" in pb.task_types
    assert pb.task_types["port_scan"].tool == "nmap"
    assert pb.terminations[0].kind == "scope_exhausted"


def test_load_playbook_with_expansions(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: with-rules
version: "1.0"
root_tasks: []
task_types:
  web_dir_enum:
    consumes:
      host: Host
      port: "OpenPort{service: http|https}"
    produces: [WebEndpoint]
    tool: feroxbuster
    args_template: {url: "{host.ip}"}
expansions:
  - id: http-enum
    on_fact: "OpenPort{service: http|https}"
    spawn: [web_dir_enum]
terminations: [scope_exhausted]
""")
    pb = load_playbook(path)
    assert len(pb.expansions) == 1
    assert pb.expansions[0].id == "http-enum"
    assert pb.expansions[0].spawn == ["web_dir_enum"]


def test_missing_required_field_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
version: "1.0"
root_tasks: []
task_types: {}
expansions: []
terminations: []
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)


def test_unknown_task_type_in_root_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: bad
version: "1.0"
root_tasks:
  - does_not_exist: {}
task_types:
  other:
    consumes: {}
    produces: []
    tool: nmap
    args_template: {}
expansions: []
terminations: [scope_exhausted]
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)


def test_unknown_spawn_in_expansion_raises(tmp_path: Path):
    path = _write(tmp_path / "p.yaml", """
name: bad
version: "1.0"
root_tasks: []
task_types:
  real:
    consumes: {}
    produces: []
    tool: nmap
    args_template: {}
expansions:
  - id: r1
    on_fact: "Host"
    spawn: [not_real]
terminations: [scope_exhausted]
""")
    with pytest.raises(PlaybookValidationError):
        load_playbook(path)
