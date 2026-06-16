"""Shared conversation logic for Mac clients and consumer devices."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from emberforge.context import ensure_request_id
from emberforge.errors import config_error, llm_error
from emberforge.http.retry import is_retryable_status, post_with_retry
from emberforge.services.personas import Persona
from emberforge.settings import Settings, get_settings


@dataclass(frozen=True)
class ConversationResult:
    request_id: str
    transcript: str
    response_text: str
    persona_id: str
    persona_name: str
    voice: dict
    display_lines: list[str]
    timestamp: str


def format_for_display(
    text: str,
    max_lines: int = 6,
    max_chars_per_line: int = 42,
) -> list[str]:
    """Break response text into short lines for small device screens."""
    wrapped = textwrap.wrap(text, width=max_chars_per_line, break_long_words=False)
    if not wrapped:
        return []
    if len(wrapped) <= max_lines:
        return wrapped
    trimmed = wrapped[: max_lines - 1]
    trimmed.append(wrapped[max_lines - 1][: max_chars_per_line - 1] + "…")
    return trimmed


def voice_to_dict(persona: Persona) -> dict:
    voice = persona.voice
    return {
        "provider": voice.provider,
        "voice": voice.voice,
        "rate": voice.rate,
        "profile": voice.profile,
        "format": None,
        "audio_url": None,
        "audio_base64": None,
    }


async def generate_reply(
    persona: Persona,
    message: str,
    *,
    settings: Settings | None = None,
    temperature: float | None = None,
    request_id: str | None = None,
) -> ConversationResult:
    """Run a single persona conversation turn."""
    resolved_settings = settings or get_settings()
    resolved_request_id = ensure_request_id(request_id)

    try:
        resolved_settings.validate_runtime()
    except RuntimeError as exc:
        raise config_error(str(exc), request_id=resolved_request_id) from exc

    resolved_temperature = temperature if temperature is not None else persona.temperature

    messages = [
        {"role": "system", "content": persona.system_prompt},
        {"role": "user", "content": message},
    ]

    payload = {
        "model": resolved_settings.xai_model,
        "messages": messages,
        "temperature": resolved_temperature,
        "max_tokens": resolved_settings.xai_max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {resolved_settings.resolved_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=resolved_settings.xai_timeout_seconds) as client:
            response = await post_with_retry(
                client,
                resolved_settings.xai_api_url,
                max_retries=resolved_settings.xai_max_retries,
                base_delay_seconds=resolved_settings.xai_retry_base_seconds,
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise llm_error("xAI request timed out", retryable=True, request_id=resolved_request_id) from exc
    except httpx.TransportError as exc:
        raise llm_error("xAI service unreachable", retryable=True, request_id=resolved_request_id) from exc

    if response.status_code >= 400:
        raise llm_error(
            f"xAI returned HTTP {response.status_code}",
            retryable=is_retryable_status(response.status_code),
            request_id=resolved_request_id,
        )

    try:
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise llm_error("Invalid response from xAI", retryable=False, request_id=resolved_request_id) from exc

    return ConversationResult(
        request_id=resolved_request_id,
        transcript=message,
        response_text=reply,
        persona_id=persona.id,
        persona_name=persona.name,
        voice=voice_to_dict(persona),
        display_lines=format_for_display(reply),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )