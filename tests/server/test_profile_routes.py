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


def test_create_accepts_and_returns_callback_ip(client):
    resp = client.post("/api/profiles", json={
        "name": "kali1", "host": "h", "port": 22,
        "username": "u", "auth_type": "password",
        "credential": "pw", "callback_ip": "10.10.14.7",
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["callback_ip"] == "10.10.14.7"

    listed = client.get("/api/profiles").json()
    assert listed[0]["callback_ip"] == "10.10.14.7"


def test_patch_callback_ip_to_null(client):
    pid = client.post("/api/profiles", json={
        "name": "k2", "host": "h", "port": 22, "username": "u",
        "auth_type": "password", "credential": "pw",
        "callback_ip": "10.0.0.1",
    }).json()["id"]
    resp = client.patch(f"/api/profiles/{pid}",
                         json={"callback_ip": None})
    assert resp.status_code == 200
    assert resp.json()["callback_ip"] is None


def test_credential_never_returned_even_with_callback_ip(client):
    client.post("/api/profiles", json={
        "name": "k3", "host": "h", "port": 22, "username": "u",
        "auth_type": "password", "credential": "secret-pw",
        "callback_ip": "10.10.14.7",
    })
    body = client.get("/api/profiles").json()[0]
    assert "credential" not in body
    assert "credential_enc" not in body
