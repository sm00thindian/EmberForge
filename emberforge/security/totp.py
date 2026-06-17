"""TOTP helpers (Google Authenticator compatible)."""

from __future__ import annotations

import pyotp


def normalize_totp_secret(secret: str) -> str:
    return secret.strip().replace(" ", "").upper()


def verify_totp_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    normalized_secret = normalize_totp_secret(secret)
    if not normalized_secret or not code:
        return False
    cleaned_code = code.strip().replace(" ", "")
    if not cleaned_code.isdigit() or len(cleaned_code) != 6:
        return False
    totp = pyotp.TOTP(normalized_secret)
    return bool(totp.verify(cleaned_code, valid_window=valid_window))


def provisioning_uri(secret: str, *, account_name: str = "EmberForge Admin") -> str:
    normalized_secret = normalize_totp_secret(secret)
    totp = pyotp.TOTP(normalized_secret)
    return totp.provisioning_uri(name=account_name, issuer_name="EmberForge")