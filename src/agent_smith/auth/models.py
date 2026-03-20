"""User model and role definitions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(BaseModel):
    username: str
    password_hash: str
    role: Role
    created_at: str  # ISO format datetime string

    @classmethod
    def create(cls, username: str, password_hash: str, role: Role) -> User:
        return cls(
            username=username,
            password_hash=password_hash,
            role=role,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class UserStore:
    """File-based user storage (JSON). Easily swappable to DB later."""

    def __init__(self, path: str = "data/users.json") -> None:
        self.path = Path(path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]")

    def _load(self) -> list[User]:
        data = json.loads(self.path.read_text())
        return [User(**u) for u in data]

    def _save(self, users: list[User]) -> None:
        self.path.write_text(
            json.dumps([u.model_dump() for u in users], indent=2)
        )

    def get_by_username(self, username: str) -> User | None:
        for user in self._load():
            if user.username == username:
                return user
        return None

    def create_user(self, user: User) -> None:
        users = self._load()
        if any(u.username == user.username for u in users):
            raise ValueError(f"User '{user.username}' already exists")
        users.append(user)
        self._save(users)

    def list_users(self) -> list[User]:
        return self._load()

    def delete_user(self, username: str) -> bool:
        users = self._load()
        filtered = [u for u in users if u.username != username]
        if len(filtered) == len(users):
            return False
        self._save(filtered)
        return True
