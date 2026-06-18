"""ElevenLabs text-to-speech for server-side device playback."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from emberforge.context import get_request_id
from emberforge.errors import tts_error
from emberforge.http.retry import is_retryable_status, post_with_retry
from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.base import TTSProvider, TTSResult
from emberforge.services.voice.profiles import get_voice_profile
from emberforge.services.voice.tts_text import apply_sentence_pauses, prepare_tts_text
from emberforge.settings import Settings


class ElevenLabsTTS(TTSProvider):
    """Synthesize speech via ElevenLabs API — returns MP3 bytes for devices."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[str, bytes] = {}

    @property
    def name(self) -> str:
        return "elevenlabs"

    def available(self) -> bool:
        return bool(self._settings.elevenlabs_api_key)

    def produces_audio(self) -> bool:
        return self.available()

    def _resolve_voice_id(self, voice: VoiceConfig) -> str | None:
        if voice.profile:
            profile = get_voice_profile(voice.profile, self._settings)
            if profile and profile.ready_for_synthesis:
                return profile.elevenlabs_voice_id
            if profile and profile.elevenlabs_voice_id and voice.provider == "elevenlabs":
                return profile.elevenlabs_voice_id
            return None

        if voice.voice:
            return voice.voice

        return self._settings.elevenlabs_default_voice_id or None

    def _cache_key(self, text: str, voice_id: str) -> str:
        digest = hashlib.sha256(f"{voice_id}:{text}".encode("utf-8")).hexdigest()
        return digest

    async def synthesize(self, text: str, voice: VoiceConfig) -> TTSResult:
        cleaned = prepare_tts_text(text, self._settings)
        cleaned = apply_sentence_pauses(cleaned, self._settings.elevenlabs_sentence_pause_seconds)
        if not cleaned:
            return TTSResult(
                provider=voice.provider,
                voice=voice.voice,
                rate=voice.rate,
                profile=voice.profile,
            )

        if not self.available():
            return TTSResult.from_voice_config(voice)

        voice_id = self._resolve_voice_id(voice)
        if not voice_id:
            return TTSResult.from_voice_config(voice)

        cache_key = self._cache_key(cleaned, voice_id)
        audio_bytes = self._cache.get(cache_key)
        if audio_bytes is None:
            audio_bytes = await self._fetch_audio(cleaned, voice_id)
            self._cache[cache_key] = audio_bytes

        return TTSResult(
            provider=voice.provider,
            voice=voice_id,
            rate=voice.rate,
            profile=voice.profile,
            format="mp3",
            audio_bytes=audio_bytes,
        )

    async def _fetch_audio(self, text: str, voice_id: str) -> bytes:
        url = f"{self._settings.elevenlabs_api_url.rstrip('/')}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self._settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload: dict[str, Any] = {
            "text": text,
            "model_id": self._settings.elevenlabs_model,
            "voice_settings": {
                "speed": self._settings.elevenlabs_speed,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.elevenlabs_timeout_seconds) as client:
                response = await post_with_retry(
                    client,
                    url,
                    max_retries=self._settings.elevenlabs_max_retries,
                    base_delay_seconds=self._settings.elevenlabs_retry_base_seconds,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise tts_error("ElevenLabs request timed out", retryable=True, request_id=get_request_id()) from exc
        except httpx.TransportError as exc:
            raise tts_error("ElevenLabs service unreachable", retryable=True, request_id=get_request_id()) from exc

        if response.status_code >= 400:
            raise tts_error(
                f"ElevenLabs returned HTTP {response.status_code}",
                retryable=is_retryable_status(response.status_code),
                request_id=get_request_id(),
            )

        return response.content