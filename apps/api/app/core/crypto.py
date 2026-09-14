"""Encrypts user-supplied provider API keys at rest using the deployment's master
key (CREDENTIAL_ENCRYPTION_KEY). No plaintext copy is ever persisted; the decrypted
value only ever exists in memory for the duration of a provider call.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialDecryptionError(RuntimeError):
    pass


def _fernet() -> Fernet:
    return Fernet(settings.credential_encryption_key.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CredentialDecryptionError("stored credential could not be decrypted") from exc


def mask_secret(plaintext: str) -> str:
    """Fixed-width mask regardless of key length: avoids leaking key length as a
    side channel, and keeps the result well within the masked_label column limit."""
    if len(plaintext) <= 4:
        return "****"
    return f"****{plaintext[-4:]}"
