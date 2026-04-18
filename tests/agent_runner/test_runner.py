"""Tests for the agent runner entrypoint."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from agent_smith.agent_runner import runner
from agent_smith.control import crypto, registry


@pytest.fixture
def setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    db_path = tmp_path / "registry.db"
    r = registry.Registry(str(db_path))
    r.migrate()
    p = r.create_profile(name="p", host="h", port=22, username="u",
                          auth_type="key",
                          credential_enc=crypto.encrypt("keydata"))
    m = r.create_mission(name="x", target="10.0.0.1",
                          playbook="skeleton_portscan.yaml",
                          kali_profile_id=p.id, agent_config={})
    a = r.create_agent(mission_id=m.id)
    r.close()
    return tmp_path, m.id, a.id, db_path


@pytest.mark.asyncio
async def test_runner_emits_lifecycle_events(setup_env, monkeypatch):
    tmp_path, mission_id, agent_id, db_path = setup_env
    monkeypatch.setattr(runner, "_build_and_run_agent",
                        AsyncMock(return_value=None))

    await runner.run(db_path=db_path, data_dir=tmp_path,
                     mission_id=mission_id, agent_id=agent_id)

    events_path = tmp_path / "missions" / mission_id / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text().strip().splitlines()]
    types = [e["type"] for e in events]
    assert types[0] == "mission.started"
    assert types[-1] == "mission.completed"


@pytest.mark.asyncio
async def test_runner_emits_failed_on_exception(setup_env, monkeypatch):
    tmp_path, mission_id, agent_id, db_path = setup_env
    async def boom(*_a, **_kw): raise RuntimeError("bang")
    monkeypatch.setattr(runner, "_build_and_run_agent",
                        AsyncMock(side_effect=boom))
    with pytest.raises(SystemExit):
        await runner.run(db_path=db_path, data_dir=tmp_path,
                         mission_id=mission_id, agent_id=agent_id)
    events_path = tmp_path / "missions" / mission_id / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text().strip().splitlines()]
    assert events[-1]["type"] == "mission.failed"
    assert "bang" in events[-1]["data"]["error"]
