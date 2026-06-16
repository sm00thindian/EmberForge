"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from emberforge import __version__
from emberforge.api.app import configure_app, create_app
from emberforge.context import ensure_request_id
from emberforge.api.routes import chat, device, health
from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.services.personas import load_personas
from emberforge.settings import Settings, get_settings


@pytest.fixture
def test_settings(monkeypatch) -> Settings:
    """Settings with a fake API key, isolated from the developer's .env."""
    monkeypatch.setenv("XAI_API_KEY", "test-key-for-pytest")
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    get_settings.cache_clear()
    return Settings()


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app(test_settings)
    return TestClient(app)


@pytest.fixture
def client_with_mock(test_settings: Settings, monkeypatch) -> TestClient:
    personas = load_personas(test_settings)
    converse = ConverseService(test_settings, personas)

    async def _fake_text(persona_id, message, **kwargs):
        request_id = ensure_request_id(kwargs.get("request_id"))
        persona = converse.resolve_persona(persona_id)
        return ConversationResult(
            request_id=request_id,
            transcript=message,
            response_text=f"Reply from {persona.name}",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say", "voice": "Samantha"},
            display_lines=["Reply from", persona.name],
            timestamp="2026-06-16T12:00:00+00:00",
        )

    monkeypatch.setattr(converse, "converse_text", AsyncMock(side_effect=_fake_text))
    monkeypatch.setattr(converse, "converse_audio", AsyncMock(side_effect=_fake_text))

    app = FastAPI(title="test", version=__version__)
    device_meta, device_audio = device.create_device_routers(test_settings, converse)
    app.include_router(health.create_health_router(test_settings))
    app.include_router(chat.create_chat_router(test_settings, converse))
    app.include_router(device_meta)
    app.include_router(device_audio)
    configure_app(app)
    return TestClient(app)