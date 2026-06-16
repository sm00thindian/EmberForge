"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from emberforge import __version__
from emberforge.api.exceptions import register_exception_handlers
from emberforge.api.middleware import RequestIDMiddleware
from emberforge.api.routes import chat, device, health
from emberforge.services.converse import ConverseService
from emberforge.services.personas import load_personas
from emberforge.settings import Settings, get_settings


def configure_app(app: FastAPI) -> None:
    """Attach cross-cutting middleware and exception handlers."""
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Used by the CLI, tests, and uvicorn."""
    resolved_settings = settings or get_settings()
    personas = load_personas(resolved_settings)
    converse = ConverseService(resolved_settings, personas)

    app = FastAPI(
        title="EmberForge Voice Companion",
        description="Persona-driven AI voice companion for Mac and consumer devices.",
        version=__version__,
    )

    device_meta_router, device_audio_router = device.create_device_routers(
        resolved_settings,
        converse,
    )

    app.include_router(health.create_health_router(resolved_settings))
    app.include_router(chat.create_chat_router(resolved_settings, converse))
    app.include_router(device_meta_router)
    app.include_router(device_audio_router)

    configure_app(app)

    app.state.settings = resolved_settings
    app.state.personas = personas
    app.state.converse = converse
    return app


# Uvicorn import string: emberforge.api.app:app
app = create_app()