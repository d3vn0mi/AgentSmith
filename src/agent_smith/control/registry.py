"""SQLite-backed registry for Kali profiles, missions, and agents."""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _new_id() -> str:
    return str(uuid.uuid4())


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class KaliProfile:
    id: str
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    credential_enc: bytes
    created_at: str
    updated_at: str


class Registry:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn = sqlite3.connect(path, isolation_level=None,
                                       check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    # ---- Schema ----

    def migrate(self) -> None:
        cur = self._conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_meta "
                     "(key TEXT PRIMARY KEY, value TEXT)")
        row = cur.execute(
            "SELECT value FROM schema_meta WHERE key='version'"
        ).fetchone()
        current = int(row["value"]) if row else 0
        if current >= SCHEMA_VERSION:
            return

        if current < 1:
            cur.executescript("""
                CREATE TABLE kali_profiles (
                    id              TEXT PRIMARY KEY,
                    name            TEXT NOT NULL UNIQUE,
                    host            TEXT NOT NULL,
                    port            INTEGER NOT NULL DEFAULT 22,
                    username        TEXT NOT NULL,
                    auth_type       TEXT NOT NULL,
                    credential_enc  BLOB NOT NULL,
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL
                );
                CREATE TABLE missions (
                    id                 TEXT PRIMARY KEY,
                    name               TEXT NOT NULL,
                    target             TEXT NOT NULL,
                    playbook           TEXT NOT NULL,
                    kali_profile_id    TEXT NOT NULL REFERENCES kali_profiles(id),
                    status             TEXT NOT NULL,
                    agent_config_json  TEXT NOT NULL,
                    created_at         TEXT NOT NULL,
                    started_at         TEXT,
                    ended_at           TEXT
                );
                CREATE TABLE agents (
                    id             TEXT PRIMARY KEY,
                    mission_id     TEXT NOT NULL REFERENCES missions(id),
                    container_id   TEXT,
                    container_name TEXT,
                    status         TEXT NOT NULL,
                    started_at     TEXT,
                    ended_at       TEXT,
                    exit_code      INTEGER
                );
                CREATE INDEX idx_missions_status ON missions(status);
                CREATE INDEX idx_agents_mission  ON agents(mission_id);
            """)

        cur.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', ?)",
            (str(SCHEMA_VERSION),),
        )

    # ---- KaliProfile CRUD ----

    def create_profile(self, *, name, host, port, username, auth_type,
                        credential_enc) -> KaliProfile:
        pid = _new_id()
        now = _now()
        try:
            self._conn.execute(
                """INSERT INTO kali_profiles
                   (id, name, host, port, username, auth_type, credential_enc,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, name, host, port, username, auth_type,
                 credential_enc, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise RegistryError(f"profile insert failed: {exc}") from exc
        result = self._load_profile(pid)
        if result is None:
            raise RegistryError("insert succeeded but load returned None")
        return result

    def get_profile(self, profile_id: str) -> Optional[KaliProfile]:
        return self._load_profile(profile_id)

    def list_profiles(self) -> list[KaliProfile]:
        rows = self._conn.execute(
            "SELECT * FROM kali_profiles ORDER BY name ASC"
        ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def update_profile(self, profile_id: str, **fields) -> KaliProfile:
        if not fields:
            result = self._load_profile(profile_id)
            if result is None:
                raise RegistryError(f"profile {profile_id} not found")
            return result
        allowed = {"name", "host", "port", "username", "auth_type", "credential_enc"}
        bad = set(fields) - allowed
        if bad:
            raise RegistryError(f"cannot update fields: {bad}")
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self._conn.execute(
            f"UPDATE kali_profiles SET {set_clause}, updated_at=? WHERE id=?",
            (*fields.values(), _now(), profile_id),
        )
        result = self._load_profile(profile_id)
        if result is None:
            raise RegistryError(f"profile {profile_id} not found")
        return result

    def delete_profile(self, profile_id: str) -> None:
        self._conn.execute("DELETE FROM kali_profiles WHERE id=?", (profile_id,))

    def _load_profile(self, profile_id: str) -> Optional[KaliProfile]:
        row = self._conn.execute(
            "SELECT * FROM kali_profiles WHERE id=?", (profile_id,)
        ).fetchone()
        return self._row_to_profile(row) if row else None

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> KaliProfile:
        return KaliProfile(
            id=row["id"], name=row["name"], host=row["host"], port=row["port"],
            username=row["username"], auth_type=row["auth_type"],
            credential_enc=bytes(row["credential_enc"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
