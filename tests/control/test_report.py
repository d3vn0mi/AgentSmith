"""Tests for Markdown report rendering."""
from __future__ import annotations

import json

import pytest

from agent_smith.control import crypto, registry, report


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    r = registry.Registry(str(tmp_path / "registry.db"))
    r.migrate()
    p = r.create_profile(name="home-kali", host="h", port=22, username="u",
                          auth_type="key", credential_enc=crypto.encrypt("k"))
    m = r.create_mission(name="HTB Paper", target="10.129.0.1",
                          playbook="skeleton_portscan.yaml",
                          kali_profile_id=p.id, agent_config={})
    d = tmp_path / "missions" / m.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "evidence.json").write_text(json.dumps({
        "flags": ["HTB{foo}"], "ports": [{"port": 80, "service": "http"}],
        "credentials": [], "vulnerabilities": [], "files": []}))
    (d / "history.jsonl").write_text(
        json.dumps({"ts": "t", "command": "nmap 10.129.0.1",
                     "exit_code": 0, "stdout_preview": "..."}) + "\n")
    return r, m, tmp_path


def test_render_includes_all_sections(fixture):
    r, m, data_dir = fixture
    text = report.render(r, m.id, data_dir=data_dir)
    assert "# Mission: HTB Paper" in text
    assert "10.129.0.1" in text
    assert "HTB{foo}" in text
    assert "nmap 10.129.0.1" in text
    assert "home-kali" in text
