"""CLI command to create the initial admin user."""

from __future__ import annotations

import os

from agent_smith.auth.models import Role, User, UserStore
from agent_smith.auth.passwords import hash_password


def seed_admin(users_file: str = "data/users.json") -> None:
    """Create the initial admin user from environment variables."""
    store = UserStore(users_file)

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not password:
        raise ValueError(
            "ADMIN_PASSWORD environment variable must be set. "
            "Example: ADMIN_PASSWORD=mypassword python -m agent_smith seed-admin"
        )

    existing = store.get_by_username(username)
    if existing:
        print(f"Admin user '{username}' already exists. Skipping.")
        return

    user = User.create(
        username=username,
        password_hash=hash_password(password),
        role=Role.ADMIN,
    )
    store.create_user(user)
    print(f"Admin user '{username}' created successfully.")
