"""Tests for _resolve_engine + runner v2 branch dispatch."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agent_smith.agent_runner import runner
from agent_smith.control import crypto, registry


@pytest.fixture
def v2_ctx(tmp_path, monkeypatch):
    """Fixture: profile + mission with playbook=htb_easy_recon.yaml (a v2 playbook)."""
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    db = tmp_path / "registry.db"
    r = registry.Registry(str(db))
    r.migrate()
    p = r.create_profile(name="p", host="h", port=22, username="u",
                          auth_type="password",
                          credential_enc=crypto.encrypt("pw"))
    m = r.create_mission(name="x", target="10.0.0.1",
                          playbook="htb_easy_recon.yaml",
                          kali_profile_id=p.id, agent_config={})
    a = r.create_agent(mission_id=m.id)
    r.close()
    return tmp_path, m.id, a.id, db


@pytest.fixture
def v1_ctx(tmp_path, monkeypatch):
    """Fixture: profile + mission with a non-existent playbook (routes to v1)."""
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    db = tmp_path / "registry.db"
    r = registry.Registry(str(db))
    r.migrate()
    p = r.create_profile(name="p", host="h", port=22, username="u",
                          auth_type="password",
                          credential_enc=crypto.encrypt("pw"))
    m = r.create_mission(name="x", target="10.0.0.1",
                          playbook="does_not_exist.yaml",
                          kali_profile_id=p.id, agent_config={})
    a = r.create_agent(mission_id=m.id)
    r.close()
    return tmp_path, m.id, a.id, db


def test_resolve_engine_returns_v2_for_known_playbook():
    class _M: playbook = "htb_easy_recon.yaml"
    assert runner._resolve_engine(_M()) == "v2"


def test_resolve_engine_returns_v1_for_missing_playbook():
    class _M: playbook = "does_not_exist.yaml"
    assert runner._resolve_engine(_M()) == "v1"


def test_resolve_engine_returns_v1_for_malformed_playbook():
    bad = Path("src/agent_smith/playbooks/_bogus.yaml")
    bad.write_text("not a real playbook")
    try:
        class _M: playbook = "_bogus.yaml"
        assert runner._resolve_engine(_M()) == "v1"
    finally:
        bad.unlink()


@pytest.mark.asyncio
async def test_runner_uses_v2_engine_when_playbook_is_v2(v2_ctx, monkeypatch):
    tmp_path, mid, aid, db = v2_ctx

    called = {"v1": False, "v2": False}

    async def fake_v2(mission, profile, data_dir, writer):
        called["v2"] = True

    async def fake_v1(mission, profile, data_dir, writer):
        called["v1"] = True

    monkeypatch.setattr(runner, "_run_v2_engine",
                        AsyncMock(side_effect=fake_v2))
    monkeypatch.setattr(runner, "_build_and_run_agent",
                        AsyncMock(side_effect=fake_v1))

    await runner.run(db_path=db, data_dir=tmp_path,
                     mission_id=mid, agent_id=aid)

    assert called["v2"] is True
    assert called["v1"] is False


@pytest.mark.asyncio
async def test_runner_uses_v1_engine_when_playbook_unknown(v1_ctx, monkeypatch):
    tmp_path, mid, aid, db = v1_ctx

    called = {"v1": False, "v2": False}

    async def fake_v2(*a, **kw): called["v2"] = True
    async def fake_v1(*a, **kw): called["v1"] = True

    monkeypatch.setattr(runner, "_run_v2_engine",
                        AsyncMock(side_effect=fake_v2))
    monkeypatch.setattr(runner, "_build_and_run_agent",
                        AsyncMock(side_effect=fake_v1))

    await runner.run(db_path=db, data_dir=tmp_path,
                     mission_id=mid, agent_id=aid)

    assert called["v1"] is True
    assert called["v2"] is False
