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
