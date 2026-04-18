"""Tests for the Fernet-based credential crypto wrapper."""

import pytest
from agent_smith.control import crypto


def test_roundtrip(monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    ct = crypto.encrypt("hunter2")
    assert ct != b"hunter2"
    assert crypto.decrypt(ct) == "hunter2"


def test_tampered_ciphertext_raises(monkeypatch):
    monkeypatch.setenv("MASTER_KEY", crypto.generate_key().decode())
    ct = bytearray(crypto.encrypt("secret"))
    ct[-1] ^= 0x01
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(bytes(ct))


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MASTER_KEY", raising=False)
    with pytest.raises(crypto.CryptoError):
        crypto.encrypt("anything")


def test_generate_key_is_valid_fernet():
    key = crypto.generate_key()
    assert len(key) == 44
