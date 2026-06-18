"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from emberforge import __version__
from emberforge.api.exceptions import register_exception_handlers
from emberforge.api.middleware import (
    ObservabilityMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    configure_security_logging,
)
from emberforge.api.routes import admin, chat, device, health, setup
from emberforge.hub.runtime import HubRuntime, build_hub
from emberforge.settings import Settings, get_settings

_SETUP_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
_SETUP_ASSETS = frozenset({"styles.css", "app.js", "favicon.svg"})


def _mount_setup_ui(app: FastAPI) -> None:
    """Serve the local setup SPA from /setup."""

    @app.get("/setup")
    @app.get("/setup/")
    async def setup_index():
        index = _SETUP_WEB_DIR / "index.html"
        if not index.exists():
            raise HTTPException(status_code=503, detail="Setup UI is not installed")
        return FileResponse(index)

    @app.get("/setup/{asset}")
    async def setup_asset(asset: str):
        if asset not in _SETUP_ASSETS:
            raise HTTPException(status_code=404, detail="Not found")
        path = _SETUP_WEB_DIR / asset
        if not path.exists():
            raise HTTPException(status_code=404, detail="Not found")
        if asset.endswith(".css"):
            media = "text/css"
        elif asset.endswith(".svg"):
            media = "image/svg+xml"
        else:
            media = "application/javascript"
        return FileResponse(path, media_type=media)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        path = _SETUP_WEB_DIR / "favicon.svg"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(path, media_type="image/svg+xml")


def configure_app(app: FastAPI) -> None:
    """Attach cross-cutting middleware and exception handlers."""
    configure_security_logging()
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    logger = logging.getLogger("emberforge")
    logger.info("emberforge_startup version=%s", __version__)
    try:
        yield
    finally:
        from emberforge.security.runtime import reset_security_state

        reset_security_state()
        logger.info("emberforge_shutdown complete")


def create_app(settings: Settings | None = None, hub: HubRuntime | None = None) -> FastAPI:
    """Build the FastAPI app. Used by the CLI, tests, and uvicorn."""
    resolved_hub = hub or build_hub(settings)
    resolved_settings = resolved_hub.settings
    personas = resolved_hub.personas
    converse = resolved_hub.converse

    app = FastAPI(
        title="EmberForge Voice Companion",
        description="Persona-driven AI voice companion for Mac and consumer devices.",
        version=__version__,
        lifespan=_app_lifespan,
    )

    device_pair_router, device_meta_router, device_audio_router = device.create_device_routers(
        resolved_settings,
        converse,
    )

    app.include_router(health.create_health_router(resolved_settings))
    app.include_router(setup.create_setup_router(resolved_settings))
    app.include_router(admin.create_admin_router(resolved_settings))
    app.include_router(chat.create_chat_router(resolved_settings, converse))
    app.include_router(device_pair_router)
    app.include_router(device_meta_router)
    app.include_router(device_audio_router)
    _mount_setup_ui(app)

    configure_app(app)

    app.state.hub = resolved_hub
    app.state.settings = resolved_settings
    app.state.personas = personas
    app.state.converse = converse
    return app


# Uvicorn import string: emberforge.api.app:app
app = create_app()