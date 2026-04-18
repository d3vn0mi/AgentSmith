"""Tests for control-plane startup reconciliation."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agent_smith.control import registry, recovery
from agent_smith.control.spawner import LiveAgent


@pytest.fixture
def db(tmp_path):
    r = registry.Registry(str(tmp_path / "registry.db"))
    r.migrate()
    yield r
    r.close()


def _mk_running_mission(db):
    p = db.create_profile(name="p", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x")
    m = db.create_mission(name="x", target="t", playbook="pb",
                           kali_profile_id=p.id, agent_config={})
    a = db.create_agent(mission_id=m.id)
    db.set_mission_status(m.id, "running", started_at=True)
    db.set_agent_running(a.id, container_id="cid-1", container_name="n")
    return m, a


def _write_event_log(tmp_path, mission_id, last_type):
    d = tmp_path / "missions" / mission_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "events.jsonl").write_text(
        json.dumps({"seq": 0, "type": "mission.started", "ts": "x",
                     "mission_id": mission_id, "agent_id": "a", "data": {}}) + "\n"
        + json.dumps({"seq": 1, "type": last_type, "ts": "x",
                       "mission_id": mission_id, "agent_id": "a", "data": {}}) + "\n"
    )


def test_live_container_leaves_rows_alone(db, tmp_path):
    m, a = _mk_running_mission(db)
    spawner = MagicMock()
    spawner.list_by_label.return_value = [
        LiveAgent(container_id="cid-1", container_name="n",
                   mission_id=m.id, agent_id=a.id)]
    recovery.reconcile(db, spawner, data_dir=tmp_path)
    assert db.get_mission(m.id).status == "running"
    assert db.get_agent(a.id).status == "running"


def test_dead_container_infers_completed(db, tmp_path):
    m, a = _mk_running_mission(db)
    _write_event_log(tmp_path, m.id, "mission.completed")
    spawner = MagicMock(); spawner.list_by_label.return_value = []
    recovery.reconcile(db, spawner, data_dir=tmp_path)
    assert db.get_mission(m.id).status == "completed"
    assert db.get_agent(a.id).status == "exited"


def test_dead_container_with_stopped_event(db, tmp_path):
    m, a = _mk_running_mission(db)
    _write_event_log(tmp_path, m.id, "mission.stopped")
    spawner = MagicMock(); spawner.list_by_label.return_value = []
    recovery.reconcile(db, spawner, data_dir=tmp_path)
    assert db.get_mission(m.id).status == "stopped"


def test_dead_container_unknown_event_marks_failed(db, tmp_path):
    m, a = _mk_running_mission(db)
    _write_event_log(tmp_path, m.id, "agent.thinking")
    spawner = MagicMock(); spawner.list_by_label.return_value = []
    recovery.reconcile(db, spawner, data_dir=tmp_path)
    assert db.get_mission(m.id).status == "failed"
