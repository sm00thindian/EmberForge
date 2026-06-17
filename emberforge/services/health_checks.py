"""Deep readiness checks for /health/ready."""

from __future__ import annotations

import shutil
from typing import Any

import httpx

from emberforge.services.llm import llm_models_probe_url, resolve_llm_config
from emberforge.services.personas import load_personas
from emberforge.services.voice.registry import get_stt_provider
from emberforge.settings import Settings


def _component(status: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status}
    payload.update(extra)
    return payload


async def check_llm(settings: Settings) -> dict[str, Any]:
    llm = resolve_llm_config(settings=settings)
    if not llm.api_key:
        return _component(
            "fail",
            message="LLM API key is not configured",
            provider=llm.provider,
        )

    url = llm_models_probe_url(llm.api_url)
    headers = {"Authorization": f"Bearer {llm.api_key}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        return _component(
            "fail",
            message="LLM request timed out",
            reachable=False,
            provider=llm.provider,
        )
    except httpx.TransportError as exc:
        return _component(
            "fail",
            message=str(exc),
            reachable=False,
            provider=llm.provider,
        )

    reachable = True
    if response.status_code == 401:
        return _component(
            "fail",
            message="LLM API key rejected",
            reachable=True,
            model=llm.model,
            api_url=llm.api_url,
            provider=llm.provider,
        )
    if response.status_code >= 500:
        return _component(
            "degraded",
            message=f"LLM returned HTTP {response.status_code}",
            reachable=True,
            model=llm.model,
            api_url=llm.api_url,
            provider=llm.provider,
        )
    if response.status_code >= 400:
        return _component(
            "ok",
            message=f"LLM reachable (HTTP {response.status_code})",
            reachable=True,
            model=llm.model,
            api_url=llm.api_url,
            provider=llm.provider,
        )

    return _component(
        "ok",
        reachable=reachable,
        model=llm.model,
        api_url=llm.api_url,
        provider=llm.provider,
    )


async def check_xai(settings: Settings) -> dict[str, Any]:
    """Backward-compatible alias for :func:`check_llm`."""
    return await check_llm(settings)


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
    llm_report = await check_llm(settings)
    components = {
        "llm": llm_report,
        "xai": llm_report,
        "whisper": check_whisper(settings),
        "disk": check_disk(settings),
        "personas": check_personas(settings),
        "elevenlabs": await check_elevenlabs(settings),
    }
    return {
        "status": aggregate_status(components),
        "components": components,
    }