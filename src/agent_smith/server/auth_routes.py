"""Authentication API routes - login, token refresh, user management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from agent_smith.auth.dependencies import get_current_user, require_role
from agent_smith.auth.jwt import create_access_token, create_refresh_token, decode_token
from agent_smith.auth.models import Role, User, UserStore
from agent_smith.auth.passwords import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Set during app startup
_jwt_secret: str = ""
_access_expiry: int = 3600
_refresh_expiry: int = 604800
_user_store: UserStore | None = None


def configure_auth_routes(
    jwt_secret: str,
    access_expiry: int,
    refresh_expiry: int,
    user_store: UserStore,
) -> None:
    global _jwt_secret, _access_expiry, _refresh_expiry, _user_store
    _jwt_secret = jwt_secret
    _access_expiry = access_expiry
    _refresh_expiry = refresh_expiry
    _user_store = user_store


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


@router.post("/login", response_model=TokenResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """Authenticate and return JWT tokens."""
    if not _user_store:
        raise HTTPException(status_code=500, detail="Auth not configured")

    user = _user_store.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.username, user.role.value, _jwt_secret, _access_expiry),
        refresh_token=create_refresh_token(user.username, _jwt_secret, _refresh_expiry),
        role=user.role.value,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest) -> TokenResponse:
    """Refresh an expired access token."""
    if not _user_store:
        raise HTTPException(status_code=500, detail="Auth not configured")

    payload = decode_token(req.refresh_token, _jwt_secret)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    username = payload.get("sub", "")
    user = _user_store.get_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.username, user.role.value, _jwt_secret, _access_expiry),
        refresh_token=create_refresh_token(user.username, _jwt_secret, _refresh_expiry),
        role=user.role.value,
    )


@router.get("/me")
async def me(user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Get current user info."""
    return {"username": user.username, "role": user.role.value}


@router.post("/users")
async def create_user(
    req: CreateUserRequest,
    _admin: Annotated[User, Depends(require_role(Role.ADMIN))],
) -> dict:
    """Create a new user (admin only)."""
    if not _user_store:
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        role = Role(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    try:
        user = User.create(
            username=req.username,
            password_hash=hash_password(req.password),
            role=role,
        )
        _user_store.create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"username": req.username, "role": req.role, "created": True}


@router.get("/users")
async def list_users(
    _admin: Annotated[User, Depends(require_role(Role.ADMIN))],
) -> list[dict]:
    """List all users (admin only)."""
    if not _user_store:
        return []
    return [
        {"username": u.username, "role": u.role.value, "created_at": u.created_at}
        for u in _user_store.list_users()
    ]
