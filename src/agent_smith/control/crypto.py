"""Fernet-based symmetric encryption for credentials at rest.

Reads MASTER_KEY from the environment (url-safe base64, 44 chars).
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class CryptoError(Exception):
    pass


def _fernet() -> Fernet:
    key = os.environ.get("MASTER_KEY")
    if not key:
        raise CryptoError("MASTER_KEY not set in environment")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise CryptoError(f"Invalid MASTER_KEY: {exc}") from exc


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes) -> str:
    try:
        return _fernet().decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise CryptoError("ciphertext tampered or wrong key") from exc
