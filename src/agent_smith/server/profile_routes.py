"""REST for Kali SSH profiles."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_smith.control import crypto
from agent_smith.control.registry import Registry, RegistryError


router = APIRouter(prefix="/api/profiles", tags=["profiles"])

_registry: Optional[Registry] = None
_auth_disabled_for_tests = False


def configure(registry: Registry, *, auth_disabled_for_tests: bool = False) -> None:
    global _registry, _auth_disabled_for_tests
    _registry = registry
    _auth_disabled_for_tests = auth_disabled_for_tests


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    host: str
    port: int = 22
    username: str
    auth_type: str
    credential: str


class ProfilePatch(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    auth_type: Optional[str] = None
    credential: Optional[str] = None


class ProfileOut(BaseModel):
    id: str
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    created_at: str
    updated_at: str


def _to_out(p) -> ProfileOut:
    return ProfileOut(
        id=p.id, name=p.name, host=p.host, port=p.port,
        username=p.username, auth_type=p.auth_type,
        created_at=p.created_at, updated_at=p.updated_at,
    )


@router.get("", response_model=list[ProfileOut])
async def list_profiles():
    assert _registry
    return [_to_out(p) for p in _registry.list_profiles()]


@router.post("", response_model=ProfileOut, status_code=201)
async def create_profile(body: ProfileIn):
    assert _registry
    if body.auth_type not in ("key", "password"):
        raise HTTPException(400, "auth_type must be 'key' or 'password'")
    try:
        p = _registry.create_profile(
            name=body.name, host=body.host, port=body.port,
            username=body.username, auth_type=body.auth_type,
            credential_enc=crypto.encrypt(body.credential))
    except RegistryError as exc:
        raise HTTPException(409, str(exc))
    return _to_out(p)


@router.patch("/{profile_id}", response_model=ProfileOut)
async def update_profile(profile_id: str, body: ProfilePatch):
    assert _registry
    fields: dict = {}
    for attr in ("name", "host", "port", "username", "auth_type"):
        v = getattr(body, attr)
        if v is not None:
            fields[attr] = v
    if body.credential is not None:
        fields["credential_enc"] = crypto.encrypt(body.credential)
    if not fields:
        p = _registry.get_profile(profile_id)
    else:
        try:
            p = _registry.update_profile(profile_id, **fields)
        except RegistryError as exc:
            raise HTTPException(404, str(exc))
    if p is None:
        raise HTTPException(404, "profile not found")
    return _to_out(p)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str):
    assert _registry
    in_use = any(m.kali_profile_id == profile_id
                  for m in _registry.list_missions())
    if in_use:
        raise HTTPException(400, "profile is in use by one or more missions")
    _registry.delete_profile(profile_id)
