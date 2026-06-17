"""Shared conversation logic for Mac clients and consumer devices."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from emberforge.context import ensure_request_id
from emberforge.errors import config_error, llm_error
from emberforge.http.retry import is_retryable_status, post_with_retry
from emberforge.services.context import ContextService
from emberforge.services.history import ConversationHistoryStore, build_llm_messages
from emberforge.observability.timing import measure_phase
from emberforge.services.llm import resolve_llm_config
from emberforge.services.tool_loop import complete_with_tools
from emberforge.services.tools import ToolService
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
    model: str
    history_turns: int = 0
    session_id: str | None = None


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
    model: str | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    clear_history: bool = False,
    history_store: ConversationHistoryStore | None = None,
    context_service: ContextService | None = None,
    tool_service: ToolService | None = None,
) -> ConversationResult:
    """Run a single persona conversation turn."""
    resolved_settings = settings or get_settings()
    resolved_request_id = ensure_request_id(request_id)

    try:
        resolved_settings.validate_runtime()
    except RuntimeError as exc:
        raise config_error(str(exc), request_id=resolved_request_id) from exc

    resolved_temperature = temperature if temperature is not None else persona.temperature
    llm_config = resolve_llm_config(
        settings=resolved_settings,
        persona=persona,
        model=model,
    )
    resolved_model = llm_config.model

    history_messages: list[dict[str, str]] = []
    if session_id and history_store is not None:
        history_messages = history_store.prepare_messages(
            session_id,
            persona.id,
            clear=clear_history,
        )

    resolved_tools = tool_service or ToolService(resolved_settings)

    system_prompt = persona.system_prompt
    extras: list[str] = []
    if resolved_tools.enabled and resolved_tools.system_instruction:
        extras.append(resolved_tools.system_instruction.strip())
    if session_id and context_service is not None and resolved_settings.context_enabled:
        context_block = await context_service.get_session_context(session_id)
        if context_block:
            extras.append(context_block)
    if extras:
        system_prompt = f"{persona.system_prompt.rstrip()}\n\n" + "\n\n".join(extras)

    messages = build_llm_messages(system_prompt, history_messages, message)

    with measure_phase("llm"):
        if resolved_tools.enabled:
            reply = await complete_with_tools(
                settings=resolved_settings,
                llm_config=llm_config,
                messages=messages,
                temperature=resolved_temperature,
                tool_service=resolved_tools,
                request_id=resolved_request_id,
            )
        else:
            payload = {
                "model": resolved_model,
                "messages": messages,
                "temperature": resolved_temperature,
                "max_tokens": resolved_settings.xai_max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {llm_config.api_key}",
                "Content-Type": "application/json",
            }

            try:
                async with httpx.AsyncClient(timeout=resolved_settings.xai_timeout_seconds) as client:
                    response = await post_with_retry(
                        client,
                        llm_config.api_url,
                        max_retries=resolved_settings.xai_max_retries,
                        base_delay_seconds=resolved_settings.xai_retry_base_seconds,
                        json=payload,
                        headers=headers,
                    )
            except httpx.TimeoutException as exc:
                raise llm_error("LLM request timed out", retryable=True, request_id=resolved_request_id) from exc
            except httpx.TransportError as exc:
                raise llm_error("LLM service unreachable", retryable=True, request_id=resolved_request_id) from exc

            if response.status_code >= 400:
                raise llm_error(
                    f"LLM returned HTTP {response.status_code}",
                    retryable=is_retryable_status(response.status_code),
                    request_id=resolved_request_id,
                )

            try:
                data = response.json()
                reply = data["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise llm_error("Invalid response from LLM", retryable=False, request_id=resolved_request_id) from exc

    history_turns = 0
    if session_id and history_store is not None:
        history_turns = history_store.record_turn(session_id, persona.id, message, reply)

    return ConversationResult(
        request_id=resolved_request_id,
        transcript=message,
        response_text=reply,
        persona_id=persona.id,
        persona_name=persona.name,
        voice=voice_to_dict(persona),
        display_lines=format_for_display(reply),
        timestamp=datetime.now(timezone.utc).isoformat(),
        model=resolved_model,
        history_turns=history_turns,
        session_id=session_id,
    )