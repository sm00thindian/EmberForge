"""Token generation and constant-time verification."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_token(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def hash_token(token: str, *, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{token}".encode("utf-8")).hexdigest()
    return digest


def verify_token(token: str, token_hash: str, *, salt: str) -> bool:
    if not token or not token_hash:
        return False
    expected = hash_token(token, salt=salt)
    return hmac.compare_digest(expected, token_hash)


def parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix) :].strip()
    return token or None