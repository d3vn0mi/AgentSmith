"""Tests for authentication."""

from agent_smith.auth.passwords import hash_password, verify_password
from agent_smith.auth.jwt import create_access_token, create_refresh_token, decode_token


def test_password_hash_and_verify():
    pw = "testpassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    secret = "test-secret-key"
    token = create_access_token("admin", "admin", secret, expires_seconds=3600)
    payload = decode_token(token, secret)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    secret = "test-secret-key"
    token = create_refresh_token("admin", secret, expires_seconds=3600)
    payload = decode_token(token, secret)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["type"] == "refresh"


def test_invalid_token():
    secret = "test-secret-key"
    payload = decode_token("invalid-token", secret)
    assert payload is None


def test_wrong_secret():
    token = create_access_token("admin", "admin", "secret1", 3600)
    payload = decode_token(token, "secret2")
    assert payload is None
