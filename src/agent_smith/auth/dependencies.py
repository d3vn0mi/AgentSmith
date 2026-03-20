"""FastAPI security dependencies for authentication and authorization."""

from __future__ import annotations

from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer

from agent_smith.auth.jwt import decode_token
from agent_smith.auth.models import Role, User, UserStore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# These are set during app startup
_jwt_secret: str = ""
_user_store: UserStore | None = None


def configure_auth(jwt_secret: str, user_store: UserStore) -> None:
    """Called at app startup to inject config."""
    global _jwt_secret, _user_store
    _jwt_secret = jwt_secret
    _user_store = user_store


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """Extract and validate the current user from JWT token."""
    payload = decode_token(token, _jwt_secret)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username or not _user_store:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = _user_store.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user


async def get_ws_user(token: str = Query(...)) -> User:
    """Extract user from WebSocket query parameter token."""
    payload = decode_token(token, _jwt_secret)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    username = payload.get("sub")
    if not username or not _user_store:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = _user_store.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user


def require_role(*roles: Role):
    """Dependency factory that checks the current user has one of the required roles."""
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized. Required: {[r.value for r in roles]}",
            )
        return user
    return checker
