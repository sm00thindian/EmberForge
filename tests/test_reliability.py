"""Reliability: retries, structured errors, deep health, request IDs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from emberforge.api.app import configure_app, create_app
from emberforge.errors import EmberForgeError, persona_not_found
from emberforge.http.retry import post_with_retry
from emberforge.services.conversation import generate_reply
from emberforge.services.health_checks import aggregate_status, check_disk, check_personas, check_whisper
from emberforge.services.personas import get_persona
from emberforge.settings import Settings


@pytest.mark.asyncio
async def test_post_with_retry_on_503(test_settings: Settings):
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await post_with_retry(
            client,
            "https://example.test/retry",
            max_retries=3,
            base_delay_seconds=0,
        )

    assert response.status_code == 200
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_generate_reply_raises_structured_llm_error(test_settings: Settings):
    ember = get_persona("ember", settings=test_settings)
    mock_response = httpx.Response(
        503,
        request=httpx.Request("POST", test_settings.xai_api_url),
    )

    with patch(
        "emberforge.services.conversation.post_with_retry",
        AsyncMock(return_value=mock_response),
    ):
        with pytest.raises(EmberForgeError) as exc_info:
            await generate_reply(ember, "Hello", settings=test_settings, request_id="req-llm")

    assert exc_info.value.code == "LLM_UNAVAILABLE"
    assert exc_info.value.retryable is True
    assert exc_info.value.request_id == "req-llm"


def test_structured_persona_not_found_response(client_with_mock):
    response = client_with_mock.post(
        "/chat",
        json={"message": "Hello", "persona": "missing"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "PERSONA_NOT_FOUND"
    assert body["retryable"] is False
    assert "request_id" in body
    assert response.headers.get("X-Request-ID") == body["request_id"]


def test_request_id_header_propagated(client_with_mock):
    response = client_with_mock.post(
        "/chat",
        json={"message": "Hello", "persona": "ember"},
        headers={"X-Request-ID": "client-request-123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "client-request-123"
    assert response.headers.get("X-Request-ID") == "client-request-123"


def test_health_ready_reports_components(test_settings: Settings, monkeypatch):
    monkeypatch.setattr(
        "emberforge.api.routes.health.run_readiness_checks",
        AsyncMock(
            return_value={
                "status": "ok",
                "components": {
                    "xai": {"status": "ok"},
                    "whisper": {"status": "ok"},
                    "disk": {"status": "ok"},
                    "personas": {"status": "ok"},
                    "elevenlabs": {"status": "skipped"},
                },
            },
        ),
    )

    app = create_app(test_settings)
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "xai" in body["components"]


def test_health_ready_returns_503_when_degraded(test_settings: Settings, monkeypatch):
    monkeypatch.setattr(
        "emberforge.api.routes.health.run_readiness_checks",
        AsyncMock(
            return_value={
                "status": "degraded",
                "components": {"xai": {"status": "degraded"}},
            },
        ),
    )

    app = create_app(test_settings)
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503


def test_health_check_helpers(test_settings: Settings):
    assert check_personas(test_settings)["status"] == "ok"
    assert check_disk(test_settings)["status"] == "ok"
    whisper = check_whisper(test_settings)
    assert whisper["status"] in {"ok", "degraded"}


def test_aggregate_status_prioritizes_failures():
    components = {
        "a": {"status": "ok"},
        "b": {"status": "degraded"},
        "c": {"status": "fail"},
    }
    assert aggregate_status(components) == "fail"


def test_persona_not_found_helper():
    err = persona_not_found("ghost", request_id="rid-1")
    assert err.to_dict()["code"] == "PERSONA_NOT_FOUND"
    assert err.to_dict()["request_id"] == "rid-1"