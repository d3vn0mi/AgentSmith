"""Tests for the /api/v2 HTTP surface."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_smith.server.v2_routes import AssessmentStore, router


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    AssessmentStore.reset(base_dir=tmp_path / "runs")
    app = FastAPI()
    app.include_router(router)
    return app


def test_create_assessment_returns_id_and_status(app):
    client = TestClient(app)
    resp = client.post("/api/v2/assessments", json={
        "playbook": "skeleton-portscan",
        "target": "203.0.113.10",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["mission_id"]
    assert body["status"] == "created"
    assert body["playbook"] == "skeleton-portscan"


def test_list_assessments_returns_created(app):
    client = TestClient(app)
    client.post("/api/v2/assessments", json={"playbook": "skeleton-portscan", "target": "1.2.3.4"})
    client.post("/api/v2/assessments", json={"playbook": "skeleton-portscan", "target": "5.6.7.8"})
    resp = client.get("/api/v2/assessments")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


def test_get_assessment_graph_empty_before_run(app):
    client = TestClient(app)
    created = client.post("/api/v2/assessments", json={
        "playbook": "skeleton-portscan", "target": "1.2.3.4",
    }).json()
    resp = client.get(f"/api/v2/assessments/{created['mission_id']}/graph")
    assert resp.status_code == 200
    g = resp.json()
    assert g["mission_id"] == created["mission_id"]
    assert g["total"] == 0


def test_get_unknown_assessment_returns_404(app):
    client = TestClient(app)
    resp = client.get("/api/v2/assessments/nope/graph")
    assert resp.status_code == 404
