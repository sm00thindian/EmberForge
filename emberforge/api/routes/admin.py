"""Admin authentication routes (TOTP / session tokens)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from emberforge.api.deps import verify_pairing_request
from emberforge.security.runtime import get_security_state
from emberforge.security.totp import provisioning_uri, verify_totp_code
from emberforge.settings import Settings


class AdminSessionRequest(BaseModel):
    totp: str = Field(..., min_length=6, max_length=8)


class AdminSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PairingCodeResponse(BaseModel):
    code: str
    expires_in: int
    message: str


class PairedDeviceResponse(BaseModel):
    device_id: str
    name: str
    paired_at: str


class DeviceListResponse(BaseModel):
    devices: list[PairedDeviceResponse]


def create_admin_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/admin/v1", tags=["admin"])

    @router.post("/session", response_model=AdminSessionResponse)
    async def create_admin_session(request: AdminSessionRequest):
        if not settings.admin_totp_secret:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=503,
                detail="TOTP is not configured (set EMBER_ADMIN_TOTP_SECRET)",
            )
        if not verify_totp_code(settings.admin_totp_secret, request.totp):
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Invalid TOTP code")

        session = get_security_state()["admin_sessions"].issue()
        expires_in = int(settings.admin_session_ttl_seconds)
        return AdminSessionResponse(access_token=session.token, expires_in=expires_in)

    @router.get("/totp/setup")
    async def totp_setup():
        if not settings.admin_totp_secret:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="EMBER_ADMIN_TOTP_SECRET is not set")
        return {
            "issuer": "EmberForge",
            "account": "EmberForge Admin",
            "provisioning_uri": provisioning_uri(settings.admin_totp_secret),
            "hint": "Scan in Google Authenticator, 1Password, or Apple Passwords.",
        }

    @router.post("/pair/code", response_model=PairingCodeResponse, dependencies=[Depends(verify_pairing_request)])
    async def issue_pairing_code():
        pairing = get_security_state()["pairing_codes"].issue()
        expires_in = int(settings.pairing_code_ttl_seconds)
        return PairingCodeResponse(
            code=pairing.code,
            expires_in=expires_in,
            message="Enter this code on the device within 5 minutes.",
        )

    @router.get("/devices", response_model=DeviceListResponse, dependencies=[Depends(verify_pairing_request)])
    async def list_devices():
        registry = get_security_state()["device_registry"]
        devices = [
            PairedDeviceResponse(
                device_id=device.device_id,
                name=device.name,
                paired_at=device.paired_at,
            )
            for device in registry.list_devices()
        ]
        return DeviceListResponse(devices=devices)

    @router.delete("/devices/{device_id}", dependencies=[Depends(verify_pairing_request)])
    async def revoke_device(device_id: str):
        from fastapi import HTTPException

        registry = get_security_state()["device_registry"]
        if not registry.revoke_device(device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        return {"revoked": True, "device_id": device_id}

    return router