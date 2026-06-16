"""Placeholder TTS for providers not yet implemented."""

from __future__ import annotations

from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.base import TTSProvider, TTSResult


class StubTTS(TTSProvider):
    """Returns voice metadata without audio — used for recorded/elevenlabs_clone until M5."""

    def __init__(self, provider_name: str) -> None:
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    def available(self) -> bool:
        return False

    async def synthesize(self, text: str, voice: VoiceConfig) -> TTSResult:
        return TTSResult(
            provider=self._name,
            voice=voice.voice,
            rate=voice.rate,
            profile=voice.profile,
        )