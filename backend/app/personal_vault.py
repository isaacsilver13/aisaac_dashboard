"""Encrypted storage for OAuth refresh tokens.

Fernet (AES-128-CBC + HMAC) with a key derived from TOKEN_ENCRYPTION_KEY, so a copy of the SQLite
file alone reveals nothing. Tokens are never returned by any route; only connected/not connected.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from . import personal_store


class VaultError(Exception):
    """Raised without detail so nothing sensitive leaks into logs or responses."""


def _fernet(key: str) -> Fernet:
    if not key:
        raise VaultError("encryption key not set")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def save_token(provider: str, token: str, key: str) -> None:
    personal_store.save_connection(provider, _fernet(key).encrypt(token.encode()).decode())


def load_token(provider: str, key: str) -> Optional[str]:
    row = personal_store.get_connection(provider)
    if row is None:
        return None
    try:
        return _fernet(key).decrypt(row["token_enc"].encode()).decode()
    except InvalidToken:
        raise VaultError("cannot decrypt") from None
