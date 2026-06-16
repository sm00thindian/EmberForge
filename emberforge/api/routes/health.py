"""Health and metadata routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from emberforge import __version__
from emberforge.services.health_checks import run_readiness_checks
from emberforge.settings import Settings


def create_health_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/")
    async def root():
        return {
            "message": "EmberForge Voice Companion is running",
            "status": "healthy",
            "version": __version__,
            "default_persona": settings.default_persona_id,
            "clients": {
                "mac": ["/personas", "/chat"],
                "device": [
                    "/device/v1/capabilities",
                    "/device/v1/personas",
                    "/device/v1/converse",
                ],
            },
        }

    @router.get("/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @router.get("/health/ready")
    async def health_ready():
        report = await run_readiness_checks(settings)
        status_code = 200 if report["status"] == "ok" else 503
        return JSONResponse(status_code=status_code, content=report)

    @router.get("/version")
    async def version():
        return {
            "name": "emberforge",
            "version": __version__,
            "device_api_version": settings.device_api_version,
        }

    return router