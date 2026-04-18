"""Tests for /api/missions and /api/playbooks."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_smith.control import crypto, registry
from agent_smith.server.mission_routes import router, configure


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    r = registry.Registry(str(tmp_path / "registry.db"))
    r.migrate()
    p = r.create_profile(name="p", host="h", port=22, username="u",
                          auth_type="key",
                          credential_enc=crypto.encrypt("k"))
    spawner = MagicMock()
    spawner.spawn.return_value = MagicMock(container_id="cid-1",
                                             container_name="name-1")
    configure(r, spawner, data_dir=tmp_path, auth_disabled_for_tests=True)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    return client, r, p, spawner, tmp_path


def test_create_mission_spawns_and_records(ctx):
    client, reg, profile, spawner, _ = ctx
    resp = client.post("/api/missions", json={
        "name": "HTB Paper", "target": "10.0.0.1",
        "playbook": "skeleton_portscan.yaml",
        "kali_profile_id": profile.id})
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "running"
    spawner.spawn.assert_called_once()


def test_list_and_get_mission(ctx):
    client, reg, profile, spawner, _ = ctx
    created = client.post("/api/missions", json={
        "name": "x", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()
    listed = client.get("/api/missions").json()
    assert [m["id"] for m in listed] == [created["id"]]
    detail = client.get(f"/api/missions/{created['id']}").json()
    assert detail["id"] == created["id"]
    assert detail["agents"][0]["container_id"] == "cid-1"


def test_stop_mission(ctx):
    client, reg, profile, spawner, _ = ctx
    created = client.post("/api/missions", json={
        "name": "x", "target": "t",
        "playbook": "skeleton_portscan.yaml",
        "kali_profile_id": profile.id}).json()
    resp = client.post(f"/api/missions/{created['id']}/stop")
    assert resp.status_code == 204
    spawner.kill.assert_called_once()
    assert reg.get_mission(created["id"]).status == "stopped"
    agents = reg.list_agents_for_mission(created["id"])
    assert agents[0].status == "killed"
    assert agents[0].ended_at is not None


def test_playbooks(ctx, tmp_path, monkeypatch):
    client, *_ = ctx
    fake = tmp_path / "playbooks"
    fake.mkdir()
    (fake / "demo.yaml").write_text("name: demo\n")
    monkeypatch.setenv("PLAYBOOKS_DIR", str(fake))
    resp = client.get("/api/playbooks")
    assert resp.status_code == 200
    names = [p["filename"] for p in resp.json()]
    assert "demo.yaml" in names


import json


def _seed_events(data_dir, mission_id, n):
    d = data_dir / "missions" / mission_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / "events.jsonl"
    with path.open("w") as fh:
        for i in range(n):
            fh.write(json.dumps({
                "ts": "2026-04-18T00:00:00Z", "seq": i,
                "type": "agent.thinking" if i % 2 else "tool.run_started",
                "mission_id": mission_id, "agent_id": "a", "data": {},
            }) + "\n")


def test_events_after(ctx):
    client, reg, profile, _, data_dir = ctx
    mid = client.post("/api/missions", json={
        "name": "x", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()["id"]
    _seed_events(data_dir, mid, 5)
    resp = client.get(f"/api/missions/{mid}/events?after=1&limit=2")
    assert resp.status_code == 200
    assert [e["seq"] for e in resp.json()] == [2, 3]


def test_events_before(ctx):
    client, reg, profile, _, data_dir = ctx
    mid = client.post("/api/missions", json={
        "name": "x", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()["id"]
    _seed_events(data_dir, mid, 5)
    resp = client.get(f"/api/missions/{mid}/events?before=4&limit=10")
    assert [e["seq"] for e in resp.json()] == [3, 2, 1, 0]


def test_events_filter_types(ctx):
    client, reg, profile, _, data_dir = ctx
    mid = client.post("/api/missions", json={
        "name": "x", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()["id"]
    _seed_events(data_dir, mid, 6)
    resp = client.get(f"/api/missions/{mid}/events?types=tool.run_started&limit=10")
    assert {e["type"] for e in resp.json()} == {"tool.run_started"}


def test_ws_replays_from_since(ctx):
    client, reg, profile, _, data_dir = ctx
    mid = client.post("/api/missions", json={
        "name": "x", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()["id"]
    _seed_events(data_dir, mid, 3)
    with client.websocket_connect(f"/ws/missions/{mid}?since=0") as ws:
        e1 = ws.receive_json()
        e2 = ws.receive_json()
        assert [e1["seq"], e2["seq"]] == [1, 2]


def test_report_md(ctx):
    client, reg, profile, _, data_dir = ctx
    mid = client.post("/api/missions", json={
        "name": "r", "target": "t", "playbook": "pb.yaml",
        "kali_profile_id": profile.id}).json()["id"]
    resp = client.get(f"/api/missions/{mid}/report.md")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "# Mission: r" in resp.text
