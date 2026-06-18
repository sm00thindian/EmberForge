"""FastAPI dependencies."""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, HTTPException, Request

from emberforge.security.request_context import is_trusted_local
from emberforge.security.runtime import get_security_state
from emberforge.security.tokens import parse_bearer
from emberforge.settings import get_settings


def _invalid_device_token() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid device token")


def _invalid_admin_token() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid admin credentials")


def verify_legacy_device_token(token: str | None, expected: str) -> bool:
    if not token or not expected:
        return False
    return hmac.compare_digest(token, expected)


def verify_device_authorization(authorization: Optional[str]) -> str | None:
    """
    Validate device bearer token.

    Returns paired device_id when matched in the registry, else None for legacy token.
    """
    settings = get_settings()
    if not settings.device_auth_required:
        return None

    token = parse_bearer(authorization)
    if not token:
        raise _invalid_device_token()

    if settings.device_token and verify_legacy_device_token(token, settings.device_token):
        return None

    registry = get_security_state()["device_registry"]
    device_id = registry.verify_device_token(token)
    if device_id:
        return device_id

    raise _invalid_device_token()


def verify_device(authorization: Optional[str] = Header(default=None)) -> None:
    """Bearer token for /device/v1/* (required in production)."""
    verify_device_authorization(authorization)


def verify_admin(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> None:
    """
    Protect Mac/developer routes from remote access in production.

    Localhost is always trusted so the Mac voice companion stays frictionless.
    Remote production access requires EMBER_ADMIN_TOKEN or a TOTP session token.
    """
    settings = get_settings()
    if not settings.is_production:
        return
    if is_trusted_local(request):
        return
    if not settings.admin_auth_configured:
        raise HTTPException(
            status_code=503,
            detail="Remote admin auth is not configured (set EMBER_ADMIN_TOKEN or EMBER_ADMIN_TOTP_SECRET)",
        )

    token = parse_bearer(authorization)
    if not token:
        raise _invalid_admin_token()

    if settings.admin_token and hmac.compare_digest(token, settings.admin_token):
        return

    sessions = get_security_state()["admin_sessions"]
    if sessions.verify(token):
        return

    raise _invalid_admin_token()


def verify_pairing_request(request: Request) -> None:
    """Pairing code issuance is localhost-only in production on maker-hosted hubs."""
    settings = get_settings()
    if not settings.deployment_profile.localhost_setup_mutations:
        return
    if not settings.is_production:
        return
    if not is_trusted_local(request):
        raise HTTPException(
            status_code=403,
            detail="Device pairing codes can only be requested from localhost",
        )


def verify_setup_request(request: Request) -> None:
    """Setup mutations are localhost-only in production on maker-hosted hubs."""
    settings = get_settings()
    if not settings.deployment_profile.allows_env_file_writes:
        raise HTTPException(
            status_code=501,
            detail="Setup configuration writes are disabled for this deployment profile",
        )
    verify_pairing_request(request)