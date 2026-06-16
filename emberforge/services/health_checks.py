"""Deep readiness checks for /health/ready."""

from __future__ import annotations

import shutil
from typing import Any

import httpx

from emberforge.services.personas import load_personas
from emberforge.services.voice.registry import get_stt_provider
from emberforge.settings import Settings


def _component(status: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status}
    payload.update(extra)
    return payload


async def check_xai(settings: Settings) -> dict[str, Any]:
    if not settings.resolved_api_key:
        return _component("fail", message="XAI_API_KEY is not configured")

    url = settings.xai_api_url.rsplit("/", 1)[0] + "/models"
    headers = {"Authorization": f"Bearer {settings.resolved_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        return _component("fail", message="xAI request timed out", reachable=False)
    except httpx.TransportError as exc:
        return _component("fail", message=str(exc), reachable=False)

    reachable = True
    if response.status_code == 401:
        return _component("fail", message="xAI API key rejected", reachable=True)
    if response.status_code >= 500:
        return _component("degraded", message=f"xAI returned HTTP {response.status_code}", reachable=True)
    if response.status_code >= 400:
        return _component("ok", message=f"xAI reachable (HTTP {response.status_code})", reachable=True)

    return _component("ok", reachable=reachable)


def check_whisper(settings: Settings) -> dict[str, Any]:
    stt = get_stt_provider(settings)
    if stt.available():
        return _component("ok", provider=stt.name, model=settings.whisper_model)
    return _component(
        "degraded",
        provider=stt.name,
        model=settings.whisper_model,
        message="faster-whisper is not installed",
    )


def check_disk(settings: Settings) -> dict[str, Any]:
    usage = shutil.disk_usage(settings.project_root)
    free_bytes = usage.free
    if free_bytes < settings.health_disk_min_bytes:
        return _component(
            "fail",
            free_bytes=free_bytes,
            min_bytes=settings.health_disk_min_bytes,
            message="Insufficient free disk space",
        )
    return _component("ok", free_bytes=free_bytes, min_bytes=settings.health_disk_min_bytes)


def check_personas(settings: Settings) -> dict[str, Any]:
    try:
        personas = load_personas(settings)
    except Exception as exc:
        return _component("fail", message=str(exc))

    if settings.default_persona_id not in personas:
        return _component(
            "fail",
            message=f"Default persona '{settings.default_persona_id}' is missing",
            count=len(personas),
        )

    return _component("ok", count=len(personas), default=settings.default_persona_id)


async def check_elevenlabs(settings: Settings) -> dict[str, Any]:
    if not settings.elevenlabs_api_key:
        return _component("skipped", message="ELEVENLABS_API_KEY is not configured")

    url = f"{settings.elevenlabs_api_url.rstrip('/')}/user"
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        return _component("fail", message="ElevenLabs request timed out", reachable=False)
    except httpx.TransportError as exc:
        return _component("fail", message=str(exc), reachable=False)

    if response.status_code == 401:
        return _component("fail", message="ElevenLabs API key rejected", reachable=True)
    if response.status_code >= 500:
        return _component("degraded", message=f"ElevenLabs returned HTTP {response.status_code}", reachable=True)
    if response.status_code >= 400:
        return _component("ok", message=f"ElevenLabs reachable (HTTP {response.status_code})", reachable=True)

    return _component("ok", reachable=True)


def aggregate_status(components: dict[str, dict[str, Any]]) -> str:
    statuses = {component["status"] for component in components.values()}
    if "fail" in statuses:
        return "fail"
    if "degraded" in statuses:
        return "degraded"
    return "ok"


async def run_readiness_checks(settings: Settings) -> dict[str, Any]:
    components = {
        "xai": await check_xai(settings),
        "whisper": check_whisper(settings),
        "disk": check_disk(settings),
        "personas": check_personas(settings),
        "elevenlabs": await check_elevenlabs(settings),
    }
    return {
        "status": aggregate_status(components),
        "components": components,
    }