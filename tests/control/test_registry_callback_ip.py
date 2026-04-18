"""Tests for the V2 migration adding callback_ip + CRUD round-trip."""
from __future__ import annotations

import sqlite3

import pytest

from agent_smith.control import registry


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "registry.db"
    r = registry.Registry(str(path))
    r.migrate()
    yield r
    r.close()


def test_callback_ip_column_exists_after_migration(db):
    cols = {row[1] for row in db._conn.execute(
        "PRAGMA table_info(kali_profiles)").fetchall()}
    assert "callback_ip" in cols


def test_create_profile_defaults_callback_ip_to_none(db):
    p = db.create_profile(name="n", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x")
    assert p.callback_ip is None


def test_create_profile_accepts_callback_ip(db):
    p = db.create_profile(name="n", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x",
                           callback_ip="10.10.14.7")
    assert p.callback_ip == "10.10.14.7"
    fetched = db.get_profile(p.id)
    assert fetched.callback_ip == "10.10.14.7"


def test_update_profile_sets_callback_ip(db):
    p = db.create_profile(name="n", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x")
    updated = db.update_profile(p.id, callback_ip="10.0.0.42")
    assert updated.callback_ip == "10.0.0.42"


def test_update_profile_clears_callback_ip(db):
    p = db.create_profile(name="n", host="h", port=22, username="u",
                           auth_type="key", credential_enc=b"x",
                           callback_ip="10.10.14.7")
    updated = db.update_profile(p.id, callback_ip=None)
    assert updated.callback_ip is None


def test_migrate_is_still_idempotent(db):
    db.migrate()
    db.migrate()
    cols = {row[1] for row in db._conn.execute(
        "PRAGMA table_info(kali_profiles)").fetchall()}
    assert "callback_ip" in cols


def test_migrate_upgrades_existing_v1_db(tmp_path):
    """Simulate an existing V1 db (no callback_ip column) being upgraded."""
    path = str(tmp_path / "old.db")
    # Hand-roll a V1 schema without callback_ip.
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("""CREATE TABLE kali_profiles (
        id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, host TEXT NOT NULL,
        port INTEGER NOT NULL DEFAULT 22, username TEXT NOT NULL,
        auth_type TEXT NOT NULL, credential_enc BLOB NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    conn.execute(
        "INSERT INTO kali_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("id-1", "n", "h", 22, "u", "key", b"x", "now", "now"),
    )
    conn.execute("""CREATE TABLE missions (
        id TEXT PRIMARY KEY, name TEXT, target TEXT, playbook TEXT,
        kali_profile_id TEXT, status TEXT, agent_config_json TEXT,
        created_at TEXT, started_at TEXT, ended_at TEXT)""")
    conn.execute("""CREATE TABLE agents (
        id TEXT PRIMARY KEY, mission_id TEXT, container_id TEXT,
        container_name TEXT, status TEXT, started_at TEXT,
        ended_at TEXT, exit_code INTEGER)""")
    conn.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES ('version', '1')")
    conn.close()

    r = registry.Registry(path)
    r.migrate()
    cols = {row[1] for row in r._conn.execute(
        "PRAGMA table_info(kali_profiles)").fetchall()}
    assert "callback_ip" in cols
    p = r.get_profile("id-1")
    assert p is not None
    assert p.callback_ip is None
    r.close()
