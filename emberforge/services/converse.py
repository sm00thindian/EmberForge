"""Unified voice conversation service for Mac clients and consumer devices."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone

from emberforge.context import ensure_request_id, get_request_id
from emberforge.errors import (
    audio_invalid,
    persona_not_found,
    stt_no_speech,
    stt_unavailable,
)
from emberforge.observability.timing import measure_phase
from emberforge.services.context import ContextService
from emberforge.services.tools import ToolService
from emberforge.services.conversation import ConversationResult, generate_reply, voice_to_dict
from emberforge.services.history import ConversationHistoryStore
from emberforge.services.llm import resolve_llm_model
from emberforge.services.personas import Persona, get_persona
from emberforge.services.voice.base import STTProvider, TTSResult
from emberforge.services.wake_phrase import WakeSessionStore, match_wake_phrase
from emberforge.services.voice.registry import (
    get_device_tts_provider,
    get_stt_provider,
    get_tts_provider,
)
from emberforge.settings import Settings, get_settings

logger = logging.getLogger("emberforge.converse")


class ConverseService:
    """
    Single code path for voice turns:
      audio/text in → STT (if needed) → LLM → TTS metadata/output
    """

    def __init__(
        self,
        settings: Settings,
        personas: dict[str, Persona],
        stt: STTProvider | None = None,
        history_store: ConversationHistoryStore | None = None,
        context_service: ContextService | None = None,
        tool_service: ToolService | None = None,
    ) -> None:
        self.settings = settings
        self.personas = personas
        self.stt = stt or get_stt_provider(settings)
        self.history = history_store or ConversationHistoryStore(
            max_turns=settings.conversation_max_turns,
            ttl_seconds=settings.conversation_session_ttl_seconds,
        )
        self.context = context_service or ContextService(settings)
        self.tools = tool_service or ToolService(settings)
        self.wake_sessions = WakeSessionStore(settings.device_wake_phrase_timeout_seconds)

    def resolve_persona(self, persona_id: str) -> Persona:
        try:
            return get_persona(persona_id, self.personas, self.settings)
        except KeyError:
            raise persona_not_found(persona_id, get_request_id()) from None

    def stt_available(self) -> bool:
        return self.stt.available()

    def server_tts_available(self) -> bool:
        return self.settings.server_tts_available

    def warm(self) -> None:
        """Prefetch STT model and context providers for lower first-turn latency."""
        if self.stt.available():
            try:
                self.stt.warm()
            except Exception:
                pass
        try:
            self.context.warm_cache()
        except Exception:
            pass

    def _ignored_audio_result(
        self,
        persona: Persona,
        transcript: str,
        *,
        request_id: str,
        session_id: str | None,
    ) -> ConversationResult:
        return ConversationResult(
            request_id=request_id,
            transcript=transcript,
            response_text="",
            persona_id=persona.id,
            persona_name=persona.name,
            voice=voice_to_dict(persona),
            display_lines=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=resolve_llm_model(settings=self.settings, persona=persona),
            session_id=session_id,
            ignored=True,
        )

    def _resolve_wake_gated_message(
        self,
        persona: Persona,
        transcript: str,
        session_id: str | None,
    ) -> str | None:
        if not self.settings.device_wake_phrase_enabled:
            return transcript

        armed = self.wake_sessions.is_armed(session_id or "")
        wake_match = match_wake_phrase(transcript, persona)
        if not armed and not wake_match.matched:
            return None

        if wake_match.matched:
            if session_id:
                self.wake_sessions.arm(session_id)
            return wake_match.command

        if session_id:
            self.wake_sessions.arm(session_id)
        return transcript

    async def converse_text(
        self,
        persona_id: str,
        message: str,
        *,
        temperature: float | None = None,
        model: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        clear_history: bool = False,
        synthesize_audio: bool = False,
        play_audio: bool = False,
    ) -> ConversationResult:
        persona = self.resolve_persona(persona_id)
        resolved_request_id = ensure_request_id(request_id)
        result = await generate_reply(
            persona,
            message,
            settings=self.settings,
            temperature=temperature,
            model=model,
            request_id=resolved_request_id,
            session_id=session_id,
            clear_history=clear_history,
            history_store=self.history,
            context_service=self.context,
            tool_service=self.tools,
        )
        return await self._enrich_with_tts(
            persona,
            result,
            synthesize_audio=synthesize_audio,
            play_audio=play_audio,
        )

    async def converse_audio(
        self,
        persona_id: str,
        audio_bytes: bytes,
        *,
        model: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        clear_history: bool = False,
        synthesize_audio: bool = False,
        play_audio: bool = False,
    ) -> ConversationResult:
        if not self.stt.available():
            raise stt_unavailable(
                "Server STT unavailable. Install faster-whisper.",
                get_request_id(),
            )

        persona = self.resolve_persona(persona_id)
        resolved_request_id = ensure_request_id(request_id)

        try:
            with measure_phase("stt"):
                transcript = self.stt.transcribe_wav(audio_bytes)
        except ValueError as exc:
            message = str(exc)
            if "No speech detected" in message:
                logger.info(
                    "wake_ignored reason=stt_no_speech session_id=%s",
                    session_id or "",
                )
                return self._ignored_audio_result(
                    persona,
                    "",
                    request_id=resolved_request_id,
                    session_id=session_id,
                )
            raise audio_invalid(message, request_id=resolved_request_id) from exc

        message = self._resolve_wake_gated_message(persona, transcript, session_id)
        if message is None:
            logger.info(
                "wake_ignored transcript=%r session_id=%s armed=%s",
                transcript,
                session_id or "",
                self.wake_sessions.is_armed(session_id or ""),
            )
            return self._ignored_audio_result(
                persona,
                transcript,
                request_id=resolved_request_id,
                session_id=session_id,
            )
        if not message.strip():
            return self._ignored_audio_result(
                persona,
                transcript,
                request_id=resolved_request_id,
                session_id=session_id,
            )

        result = await generate_reply(
            persona,
            message,
            settings=self.settings,
            model=model,
            request_id=resolved_request_id,
            session_id=session_id,
            clear_history=clear_history,
            history_store=self.history,
            context_service=self.context,
            tool_service=self.tools,
            tools_enabled=self.settings.device_tools_enabled,
            max_tokens=self.settings.device_max_tokens,
        )
        enriched = await self._enrich_with_tts(
            persona,
            result,
            synthesize_audio=synthesize_audio,
            play_audio=play_audio,
        )
        if session_id:
            self.wake_sessions.arm(session_id)
        return enriched

    async def _enrich_with_tts(
        self,
        persona: Persona,
        result: ConversationResult,
        *,
        synthesize_audio: bool,
        play_audio: bool,
    ) -> ConversationResult:
        with measure_phase("tts"):
            tts_result = TTSResult.from_voice_config(persona.voice)

            if synthesize_audio:
                tts, voice_config = get_device_tts_provider(persona.voice, self.settings)
                if tts.produces_audio():
                    tts_result = await tts.synthesize(result.response_text, voice_config)

            if play_audio and not tts_result.audio_bytes:
                tts = get_tts_provider(persona.voice, self.settings)
                tts_result = await tts.synthesize(result.response_text, persona.voice)

        return replace(result, voice=tts_result.to_voice_dict())


def create_converse_service(
    settings: Settings | None = None,
    personas: dict[str, Persona] | None = None,
) -> ConverseService:
    resolved_settings = settings or get_settings()
    from emberforge.services.personas import load_personas

    resolved_personas = personas or load_personas(resolved_settings)
    return ConverseService(resolved_settings, resolved_personas)