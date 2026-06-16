"""FastAPI dependencies."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from emberforge.settings import get_settings


def verify_device(authorization: Optional[str] = Header(default=None)) -> None:
    """Optional bearer token for device auth. Open if EMBER_DEVICE_TOKEN is unset."""
    settings = get_settings()
    if not settings.device_token:
        return
    if authorization != f"Bearer {settings.device_token}":
        raise HTTPException(status_code=401, detail="Invalid device token")