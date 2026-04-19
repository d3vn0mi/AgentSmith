"""Tests for the command_template override on TaskTypeSpec."""
from __future__ import annotations

from agent_smith.executor.executor import default_command_builder
from agent_smith.scenarios.playbook import TaskTypeSpec


def _spec(**kwargs) -> TaskTypeSpec:
    defaults = dict(
        name="t", consumes={}, produces=[], tool="dummy",
        args_template={}, timeout=60, parser=None,
    )
    defaults.update(kwargs)
    return TaskTypeSpec(**defaults)


def test_command_template_renders_with_args():
    spec = _spec(
        tool="nmap",
        command_template="nmap -sV -T4 -oX - {target}",
        args_template={"target": "{target}"},
    )
    cmd = default_command_builder(spec, {"target": "10.0.0.1"})
    assert cmd == "nmap -sV -T4 -oX - 10.0.0.1"


def test_command_template_falls_back_to_kv_when_absent():
    spec = _spec(
        tool="nmap",
        args_template={"target": "{target}"},
    )
    cmd = default_command_builder(spec, {"target": "10.0.0.1"})
    assert cmd == "nmap --target=10.0.0.1"


def test_command_template_leaves_awk_literals_alone():
    """Bash templates may contain {...} that isn't a placeholder."""
    spec = _spec(
        tool="bash",
        command_template=(
            "IP=$(ip -4 addr show tun0 | awk '/inet /{print $2}' | cut -d/ -f1); "
            "echo $IP"
        ),
        args_template={},
    )
    cmd = default_command_builder(spec, {})
    # The awk body must survive verbatim.
    assert "{print $2}" in cmd
    assert "/inet /" in cmd


def test_command_template_substitutes_known_keys_leaves_unknown_alone():
    spec = _spec(
        tool="bash",
        command_template="host={host} note={unknown_key} awk='{print $1}'",
        args_template={},
    )
    cmd = default_command_builder(spec, {"host": "10.0.0.1"})
    assert "host=10.0.0.1" in cmd
    assert "note={unknown_key}" in cmd   # literal — no key in args
    assert "{print $1}" in cmd             # awk literal


def test_command_template_ignores_dotted_placeholders():
    """{port.host_ip} style placeholders are resolved by the controller before
    reaching the builder. The builder must pass them through if it sees one."""
    spec = _spec(
        tool="bash",
        command_template="x={port.host_ip}",
        args_template={},
    )
    cmd = default_command_builder(spec, {"port": "whatever"})
    # The dotted placeholder is not a valid \w+ — leave it alone.
    assert cmd == "x={port.host_ip}"
