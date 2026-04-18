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


@dataclass(frozen=True)
class Mission:
    id: str
    name: str
    target: str
    playbook: str
    kali_profile_id: str
    status: str
    agent_config: dict
    created_at: str
    started_at: Optional[str]
    ended_at: Optional[str]


@dataclass(frozen=True)
class Agent:
    id: str
    mission_id: str
    container_id: Optional[str]
    container_name: Optional[str]
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]
    exit_code: Optional[int]


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

    # ---- Mission CRUD ----

    def create_mission(self, *, name, target, playbook,
                        kali_profile_id, agent_config) -> Mission:
        mid = _new_id()
        now = _now()
        try:
            self._conn.execute(
                """INSERT INTO missions
                   (id, name, target, playbook, kali_profile_id, status,
                    agent_config_json, created_at)
                   VALUES (?, ?, ?, ?, ?, 'created', ?, ?)""",
                (mid, name, target, playbook, kali_profile_id,
                 json.dumps(agent_config), now),
            )
        except sqlite3.IntegrityError as exc:
            raise RegistryError(f"mission insert failed: {exc}") from exc
        result = self.get_mission(mid)
        if result is None:
            raise RegistryError("insert ok but load None")
        return result

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        row = self._conn.execute(
            "SELECT * FROM missions WHERE id=?", (mission_id,)
        ).fetchone()
        return self._row_to_mission(row) if row else None

    def list_missions(self, *, status: Optional[str] = None) -> list[Mission]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM missions WHERE status=? ORDER BY created_at DESC",
                (status,)).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM missions ORDER BY created_at DESC").fetchall()
        return [self._row_to_mission(r) for r in rows]

    def set_mission_status(self, mission_id, status, *,
                            started_at=False, ended_at=False) -> None:
        parts = ["status=?"]
        params: list = [status]
        if started_at:
            parts.append("started_at=?"); params.append(_now())
        if ended_at:
            parts.append("ended_at=?"); params.append(_now())
        params.append(mission_id)
        self._conn.execute(
            f"UPDATE missions SET {', '.join(parts)} WHERE id=?", tuple(params))

    @staticmethod
    def _row_to_mission(row: sqlite3.Row) -> Mission:
        return Mission(
            id=row["id"], name=row["name"], target=row["target"],
            playbook=row["playbook"],
            kali_profile_id=row["kali_profile_id"], status=row["status"],
            agent_config=json.loads(row["agent_config_json"]),
            created_at=row["created_at"],
            started_at=row["started_at"], ended_at=row["ended_at"],
        )

    # ---- Agent CRUD ----

    def create_agent(self, *, mission_id: str) -> Agent:
        aid = _new_id()
        self._conn.execute(
            "INSERT INTO agents (id, mission_id, status) VALUES (?, ?, 'pending')",
            (aid, mission_id),
        )
        result = self.get_agent(aid)
        if result is None:
            raise RegistryError("agent insert ok but load None")
        return result

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        row = self._conn.execute(
            "SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        return self._row_to_agent(row) if row else None

    def list_agents(self, *, statuses: tuple[str, ...] = ()) -> list[Agent]:
        if statuses:
            placeholders = ", ".join("?" * len(statuses))
            rows = self._conn.execute(
                f"SELECT * FROM agents WHERE status IN ({placeholders})",
                statuses).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM agents").fetchall()
        return [self._row_to_agent(r) for r in rows]

    def list_agents_for_mission(self, mission_id: str) -> list[Agent]:
        rows = self._conn.execute(
            "SELECT * FROM agents WHERE mission_id=?", (mission_id,)
        ).fetchall()
        return [self._row_to_agent(r) for r in rows]

    def set_agent_running(self, agent_id, *, container_id, container_name) -> None:
        self._conn.execute(
            """UPDATE agents
               SET container_id=?, container_name=?, status='running',
                   started_at=?
               WHERE id=?""",
            (container_id, container_name, _now(), agent_id))

    def close_agent(self, agent_id, *, status, exit_code=None) -> None:
        self._conn.execute(
            "UPDATE agents SET status=?, ended_at=?, exit_code=? WHERE id=?",
            (status, _now(), exit_code, agent_id))

    @staticmethod
    def _row_to_agent(row: sqlite3.Row) -> Agent:
        return Agent(
            id=row["id"], mission_id=row["mission_id"],
            container_id=row["container_id"],
            container_name=row["container_name"],
            status=row["status"], started_at=row["started_at"],
            ended_at=row["ended_at"], exit_code=row["exit_code"])
