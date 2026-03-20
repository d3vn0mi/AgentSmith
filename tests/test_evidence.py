"""Tests for the evidence store."""

from agent_smith.core.evidence import Credential, EvidenceStore, Port, Vulnerability


def test_add_port():
    store = EvidenceStore()
    store.add_port(Port(number=80, protocol="tcp", state="open", service="http"))
    assert len(store.ports) == 1
    assert store.ports[0].number == 80


def test_no_duplicate_ports():
    store = EvidenceStore()
    store.add_port(Port(number=80, protocol="tcp", state="open", service="http"))
    store.add_port(Port(number=80, protocol="tcp", state="open", service="http"))
    assert len(store.ports) == 1


def test_add_flag():
    store = EvidenceStore()
    assert not store.has_user_flag
    store.add_flag("user", "abc123")
    assert store.has_user_flag
    assert store.flags["user"] == "abc123"


def test_is_complete():
    store = EvidenceStore()
    assert not store.is_complete
    store.add_flag("user", "abc")
    assert not store.is_complete
    store.add_flag("root", "def")
    assert store.is_complete


def test_summary_contains_ports():
    store = EvidenceStore()
    store.add_port(Port(number=22, protocol="tcp", state="open", service="ssh"))
    summary = store.summary()
    assert "22/tcp" in summary
    assert "ssh" in summary


def test_to_dict():
    store = EvidenceStore()
    store.add_port(Port(number=443, protocol="tcp", state="open", service="https", version="nginx"))
    store.add_flag("user", "flag{test}")
    d = store.to_dict()
    assert len(d["ports"]) == 1
    assert d["flags"]["user"] == "flag{test}"


def test_add_credential():
    store = EvidenceStore()
    store.add_credential(Credential(username="admin", password="pass", context="ssh", source="brute"))
    assert len(store.credentials) == 1
    assert store.credentials[0].username == "admin"


def test_add_vulnerability():
    store = EvidenceStore()
    store.add_vulnerability(Vulnerability(name="CVE-2021-1234", service="http", severity="critical"))
    assert len(store.vulnerabilities) == 1
