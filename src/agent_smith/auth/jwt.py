"""JWT token creation and validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt


def create_access_token(
    username: str,
    role: str,
    secret: str,
    expires_seconds: int = 3600,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(
    username: str,
    secret: str,
    expires_seconds: int = 604800,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
    payload = {
        "sub": username,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
