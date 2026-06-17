"""Local setup website API (/setup/v1)."""

from __future__ import annotations

from pathlib import Path

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from emberforge.api.deps import verify_setup_request
from emberforge.config.env_file import update_env_file
from emberforge.security.totp import provisioning_uri
from emberforge.services.context_setup import _format_place, geocode_location
from emberforge.services.setup_status import (
    _CONFIG_KEYS,
    _SENSITIVE_KEYS,
    build_config_snapshot,
    build_setup_status,
    mask_secret,
)
from emberforge.settings import Settings, get_settings


class ConfigPatchRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class LocationSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)


class LocationSaveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    index: int = Field(default=0, ge=0, le=4)


class ProfileUpdateRequest(BaseModel):
    content: str


class TotpGenerateResponse(BaseModel):
    secret: str
    provisioning_uri: str
    masked_secret: str


def _env_path(settings: Settings) -> Path:
    return settings.project_root / ".env"


def _profile_path(settings: Settings) -> Path:
    profile = settings.context_profile_file
    path = Path(profile)
    if path.is_absolute():
        return path
    return settings.project_root / profile


def _allowed_config_keys() -> frozenset[str]:
    return frozenset(_CONFIG_KEYS)


def create_setup_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/setup/v1", tags=["setup"])

    @router.get("/status")
    async def setup_status():
        current = get_settings()
        return build_setup_status(current)

    @router.get("/config")
    async def get_config():
        current = get_settings()
        return {
            "env_path": str(_env_path(current)),
            "values": build_config_snapshot(current, mask_secrets=True),
        }

    @router.patch("/config", dependencies=[Depends(verify_setup_request)])
    async def patch_config(request: ConfigPatchRequest):
        current = get_settings()
        allowed = _allowed_config_keys()
        updates: dict[str, str] = {}
        for key, value in request.values.items():
            if key not in allowed:
                raise HTTPException(status_code=400, detail=f"Unsupported config key: {key}")
            if key in _SENSITIVE_KEYS and value.startswith("••••"):
                continue
            updates[key] = value.strip()

        if not updates:
            return {"updated": [], "values": build_config_snapshot(current, mask_secrets=True)}

        update_env_file(_env_path(current), updates)
        get_settings.cache_clear()
        refreshed = get_settings()
        return {
            "updated": sorted(updates.keys()),
            "values": build_config_snapshot(refreshed, mask_secrets=True),
        }

    @router.post("/location/search")
    async def search_location(request: LocationSearchRequest):
        matches = geocode_location(request.query)
        return {
            "query": request.query,
            "matches": [
                {
                    "index": index,
                    "name": _format_place(match),
                    "latitude": match.latitude,
                    "longitude": match.longitude,
                    "timezone": match.timezone,
                    "country": match.country,
                    "admin1": match.admin1,
                }
                for index, match in enumerate(matches)
            ],
        }

    @router.post("/location", dependencies=[Depends(verify_setup_request)])
    async def save_location(request: LocationSaveRequest):
        matches = geocode_location(request.query)
        if not matches:
            raise HTTPException(status_code=404, detail=f"No matches for '{request.query}'")
        if request.index >= len(matches):
            raise HTTPException(status_code=400, detail="index out of range")

        chosen = matches[request.index]
        location_name = _format_place(chosen)
        updates = {
            "EMBER_CONTEXT_ENABLED": "true",
            "EMBER_LAT": f"{chosen.latitude:.4f}",
            "EMBER_LON": f"{chosen.longitude:.4f}",
            "EMBER_LOCATION_NAME": location_name,
        }
        if chosen.timezone:
            updates["EMBER_TIMEZONE"] = chosen.timezone

        current = get_settings()
        update_env_file(_env_path(current), updates)
        get_settings.cache_clear()

        return {
            "saved": True,
            "location": {
                "name": location_name,
                "latitude": chosen.latitude,
                "longitude": chosen.longitude,
                "timezone": chosen.timezone,
            },
        }

    @router.get("/profile")
    async def get_profile():
        current = get_settings()
        path = _profile_path(current)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return {"path": str(path), "content": content}

    @router.put("/profile", dependencies=[Depends(verify_setup_request)])
    async def put_profile(request: ProfileUpdateRequest):
        current = get_settings()
        path = _profile_path(current)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(request.content, encoding="utf-8")
        return {"saved": True, "path": str(path)}

    @router.post("/totp/generate", dependencies=[Depends(verify_setup_request)])
    async def generate_totp_secret():
        secret = pyotp.random_base32()
        return TotpGenerateResponse(
            secret=secret,
            provisioning_uri=provisioning_uri(secret),
            masked_secret=mask_secret(secret),
        )

    return router