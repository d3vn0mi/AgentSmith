"""End-to-end sanity check against a locally running stack.

Gated on `RUN_E2E=1` so it doesn't run in the default pytest invocation.
Requires the stack already be up and an admin user to be seeded.
"""
from __future__ import annotations

import os
import time

import httpx
import pytest


@pytest.mark.skipif(not os.environ.get("RUN_E2E"),
                     reason="E2E disabled unless RUN_E2E=1")
def test_create_mission_end_to_end():
    base = os.environ.get("E2E_BASE_URL", "http://localhost:8080")
    login = httpx.post(
        f"{base}/api/auth/login",
        data={"username": os.environ.get("ADMIN_USERNAME", "admin"),
               "password": os.environ["ADMIN_PASSWORD"]})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profiles = httpx.get(f"{base}/api/profiles", headers=headers).json()
    if not profiles:
        pytest.skip("E2E needs an existing kali profile")

    resp = httpx.post(
        f"{base}/api/missions", headers=headers,
        json={"name": "e2e", "target": "127.0.0.1",
              "playbook": "skeleton_portscan.yaml",
              "kali_profile_id": profiles[0]["id"]})
    assert resp.status_code == 201, resp.text
    mid = resp.json()["id"]

    for _ in range(60):
        r = httpx.get(f"{base}/api/missions/{mid}", headers=headers).json()
        if r["status"] in ("running", "completed", "failed"):
            break
        time.sleep(1)
    assert r["status"] in ("running", "completed", "failed")

    httpx.post(f"{base}/api/missions/{mid}/stop", headers=headers)
