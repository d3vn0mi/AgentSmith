"""Tests for KaliSession and Shell fact factories."""
from __future__ import annotations

from agent_smith.evidence.facts import KaliSession, Shell


def test_kalisession_canonical_key_by_session_id():
    a = KaliSession.new(
        session_id="agentsmith-abcd1234-listen-01",
        role="listener", status="starting", kali_host="10.0.0.5",
    )
    b = KaliSession.new(
        session_id="agentsmith-abcd1234-listen-01",
        role="shell", status="live", kali_host="10.0.0.5",
    )
    assert a.canonical_key == b.canonical_key == \
        "session:agentsmith-abcd1234-listen-01"
    assert a.payload["role"] == "listener"
    assert b.payload["role"] == "shell"


def test_kalisession_default_metadata_is_empty_dict():
    f = KaliSession.new(
        session_id="s", role="runner", status="live", kali_host="h",
    )
    assert f.payload["metadata"] == {}


def test_kalisession_metadata_preserved():
    f = KaliSession.new(
        session_id="s", role="runner", status="live", kali_host="h",
        metadata={"pid": 1234, "started_at": "now"},
    )
    assert f.payload["metadata"] == {"pid": 1234, "started_at": "now"}


def test_shell_canonical_key_by_session_id():
    a = Shell.new(
        session_id="sid-1", target_host="10.129.0.1",
        listener_port=4412, callback_ip="10.10.14.7",
    )
    b = Shell.new(
        session_id="sid-1", target_host="10.129.0.1",
        listener_port=4412, callback_ip="10.10.14.7",
        target_user="www-data", interactive=True, status="dead",
    )
    assert a.canonical_key == b.canonical_key == "shell:sid-1"


def test_shell_defaults():
    f = Shell.new(
        session_id="sid", target_host="t", listener_port=4400,
        callback_ip="c",
    )
    assert f.payload["target_user"] is None
    assert f.payload["interactive"] is False
    assert f.payload["status"] == "live"


def test_shell_full_payload():
    f = Shell.new(
        session_id="sid", target_host="10.129.0.1",
        listener_port=4412, callback_ip="10.10.14.7",
        target_user="root", interactive=True, status="live",
    )
    assert f.payload == {
        "session_id": "sid", "target_host": "10.129.0.1",
        "listener_port": 4412, "callback_ip": "10.10.14.7",
        "target_user": "root", "interactive": True, "status": "live",
    }
