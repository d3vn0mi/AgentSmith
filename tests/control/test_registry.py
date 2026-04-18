"""Tests for the SQLite registry DAO."""
from __future__ import annotations

import pytest
from agent_smith.control import registry


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "registry.db"
    r = registry.Registry(str(path))
    r.migrate()
    yield r
    r.close()


def test_migrate_is_idempotent(db):
    db.migrate()
    db.migrate()


def test_create_and_get_profile(db):
    p = db.create_profile(name="home-kali", host="10.0.0.5", port=22,
                           username="root", auth_type="key",
                           credential_enc=b"CIPHER")
    assert p.id
    assert p.name == "home-kali"
    assert p.credential_enc == b"CIPHER"
    assert db.get_profile(p.id) == p


def test_list_profiles(db):
    db.create_profile(name="a", host="h", port=22, username="u",
                       auth_type="key", credential_enc=b"x")
    db.create_profile(name="b", host="h", port=22, username="u",
                       auth_type="key", credential_enc=b"y")
    names = sorted(p.name for p in db.list_profiles())
    assert names == ["a", "b"]


def test_duplicate_profile_name_raises(db):
    db.create_profile(name="dup", host="h", port=22, username="u",
                       auth_type="key", credential_enc=b"x")
    with pytest.raises(registry.RegistryError):
        db.create_profile(name="dup", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"y")


def test_update_profile(db):
    p = db.create_profile(name="orig", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x")
    updated = db.update_profile(p.id, host="new.host", credential_enc=b"new")
    assert updated.host == "new.host"
    assert updated.credential_enc == b"new"
    assert updated.name == "orig"


def test_delete_profile(db):
    p = db.create_profile(name="gone", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x")
    db.delete_profile(p.id)
    assert db.get_profile(p.id) is None


def _mk_profile(db):
    return db.create_profile(name="p", host="h", port=22, username="u",
                              auth_type="key", credential_enc=b"x")


def test_create_mission(db):
    profile = _mk_profile(db)
    m = db.create_mission(name="HTB Paper", target="10.129.0.1",
                           playbook="skeleton_portscan.yaml",
                           kali_profile_id=profile.id,
                           agent_config={"max_iterations": 50})
    assert m.id
    assert m.status == "created"
    assert m.agent_config == {"max_iterations": 50}


def test_list_missions_filter_by_status(db):
    p = _mk_profile(db)
    m1 = db.create_mission(name="a", target="t", playbook="pb",
                            kali_profile_id=p.id, agent_config={})
    m2 = db.create_mission(name="b", target="t", playbook="pb",
                            kali_profile_id=p.id, agent_config={})
    db.set_mission_status(m1.id, "running", started_at=True)

    running = db.list_missions(status="running")
    assert [m.id for m in running] == [m1.id]
    all_ms = db.list_missions()
    assert {m.id for m in all_ms} == {m1.id, m2.id}


def test_set_mission_status_terminal(db):
    p = _mk_profile(db)
    m = db.create_mission(name="x", target="t", playbook="pb",
                          kali_profile_id=p.id, agent_config={})
    db.set_mission_status(m.id, "running", started_at=True)
    db.set_mission_status(m.id, "completed", ended_at=True)
    fresh = db.get_mission(m.id)
    assert fresh.status == "completed"
    assert fresh.ended_at is not None


def test_create_and_update_agent(db):
    p = _mk_profile(db)
    m = db.create_mission(name="x", target="t", playbook="pb",
                          kali_profile_id=p.id, agent_config={})
    a = db.create_agent(mission_id=m.id)
    assert a.status == "pending"
    assert a.container_id is None

    db.set_agent_running(a.id, container_id="cid-123",
                          container_name="agentsmith-agent-x")
    fresh = db.get_agent(a.id)
    assert fresh.status == "running"
    assert fresh.container_id == "cid-123"


def test_close_agent(db):
    p = _mk_profile(db)
    m = db.create_mission(name="x", target="t", playbook="pb",
                          kali_profile_id=p.id, agent_config={})
    a = db.create_agent(mission_id=m.id)
    db.set_agent_running(a.id, container_id="c", container_name="n")
    db.close_agent(a.id, status="exited", exit_code=0)
    fresh = db.get_agent(a.id)
    assert fresh.status == "exited"
    assert fresh.exit_code == 0
    assert fresh.ended_at is not None


def test_list_agents_by_status(db):
    p = _mk_profile(db)
    m = db.create_mission(name="x", target="t", playbook="pb",
                          kali_profile_id=p.id, agent_config={})
    a1 = db.create_agent(mission_id=m.id)
    a2 = db.create_agent(mission_id=m.id)
    db.set_agent_running(a1.id, container_id="c1", container_name="n1")
    running = db.list_agents(statuses=("pending", "running"))
    assert {a.id for a in running} == {a1.id, a2.id}
