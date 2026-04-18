"""Tests for /api/playbooks returning parsed YAML metadata."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_smith.control import crypto, registry
from agent_smith.server.mission_routes import router, configure


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    r = registry.Registry(str(tmp_path / "registry.db"))
    r.migrate()
    spawner = MagicMock()
    configure(r, spawner, data_dir=tmp_path, auth_disabled_for_tests=True)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_playbooks_returns_name_description_phases(client, tmp_path, monkeypatch):
    pb_dir = tmp_path / "playbooks"
    pb_dir.mkdir()
    (pb_dir / "demo.yaml").write_text(
        "name: Demo Playbook\ndescription: A demo scan.\nphases: [recon, enumeration]\ntasks: []\n"
    )
    monkeypatch.setenv("PLAYBOOKS_DIR", str(pb_dir))

    resp = client.get("/api/playbooks")
    assert resp.status_code == 200

    entries = resp.json()
    demo = next((e for e in entries if e["filename"] == "demo.yaml"), None)
    assert demo is not None, f"demo.yaml not in response: {entries}"
    assert demo["name"] == "Demo Playbook"
    assert demo["description"] == "A demo scan."
    assert demo["phases"] == ["recon", "enumeration"]


def test_playbooks_graceful_when_no_metadata(client, tmp_path, monkeypatch):
    pb_dir = tmp_path / "playbooks2"
    pb_dir.mkdir()
    (pb_dir / "bare.yaml").write_text("tasks: []\n")
    monkeypatch.setenv("PLAYBOOKS_DIR", str(pb_dir))

    resp = client.get("/api/playbooks")
    assert resp.status_code == 200

    entries = resp.json()
    bare = next((e for e in entries if e["filename"] == "bare.yaml"), None)
    assert bare is not None
    assert bare["name"] == "bare"        # falls back to stem
    assert bare["description"] == ""
    assert bare["phases"] == []
