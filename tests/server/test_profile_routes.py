"""Tests for /api/profiles."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_smith.control import crypto, registry
from agent_smith.server.profile_routes import router, configure


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    r = registry.Registry(str(tmp_path / "registry.db"))
    r.migrate()
    configure(r, auth_disabled_for_tests=True)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_create_and_list_profile(client):
    resp = client.post("/api/profiles", json={
        "name": "home-kali", "host": "10.0.0.5", "port": 22,
        "username": "root", "auth_type": "key", "credential": "KEY"})
    assert resp.status_code == 201
    body = client.get("/api/profiles").json()
    assert len(body) == 1
    assert body[0]["name"] == "home-kali"
    assert "credential" not in body[0]
    assert "credential_enc" not in body[0]


def test_update_profile(client):
    pid = client.post("/api/profiles", json={
        "name": "n", "host": "h", "port": 22, "username": "u",
        "auth_type": "key", "credential": "k"}).json()["id"]
    resp = client.patch(f"/api/profiles/{pid}", json={"host": "new.host"})
    assert resp.status_code == 200
    assert resp.json()["host"] == "new.host"


def test_delete_profile(client):
    pid = client.post("/api/profiles", json={
        "name": "n", "host": "h", "port": 22, "username": "u",
        "auth_type": "key", "credential": "k"}).json()["id"]
    resp = client.delete(f"/api/profiles/{pid}")
    assert resp.status_code == 204
    assert client.get("/api/profiles").json() == []
