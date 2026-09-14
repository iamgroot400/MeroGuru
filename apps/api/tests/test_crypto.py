from __future__ import annotations

from cryptography.fernet import Fernet

from app.core import crypto


def test_mask_secret_is_fixed_width_regardless_of_key_length(monkeypatch):
    short_key = "abcd1234"
    long_key = "sk-" + "x" * 200  # realistic long provider key
    assert len(crypto.mask_secret(short_key)) <= 20
    assert len(crypto.mask_secret(long_key)) <= 20
    assert crypto.mask_secret(long_key).endswith(long_key[-4:])


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(crypto.settings, "credential_encryption_key", Fernet.generate_key().decode())
    secret = "super-secret-api-key"
    encrypted = crypto.encrypt_secret(secret)
    assert encrypted != secret
    assert crypto.decrypt_secret(encrypted) == secret
