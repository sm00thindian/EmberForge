"""Voice pipeline provider interfaces."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

from emberforge.services.personas import VoiceConfig


@runtime_checkable
class STTProvider(Protocol):
    """Transcribe audio into text."""

    @property
    def name(self) -> str: ...

    def available(self) -> bool: ...

    def transcribe_wav(self, audio_bytes: bytes) -> str: ...

    def transcribe_array(self, audio: np.ndarray, sample_rate: int = 16_000) -> str: ...


class TTSProvider(ABC):
    """Synthesize or play persona voice output."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    async def synthesize(self, text: str, voice: VoiceConfig) -> TTSResult: ...

    def produces_audio(self) -> bool:
        """Whether this provider returns playable audio bytes (for devices)."""
        return False


@dataclass(frozen=True)
class TTSResult:
    """Output of a TTS provider — metadata now, audio bytes when cloning is wired."""

    provider: str
    voice: str | None = None
    rate: int | None = None
    profile: str | None = None
    format: str | None = None
    audio_bytes: bytes | None = None
    played_locally: bool = False

    @classmethod
    def from_voice_config(cls, voice: VoiceConfig) -> TTSResult:
        return cls(
            provider=voice.provider,
            voice=voice.voice,
            rate=voice.rate,
            profile=voice.profile,
        )

    def to_voice_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "voice": self.voice,
            "rate": self.rate,
            "profile": self.profile,
            "format": self.format,
            "audio_url": None,
            "audio_base64": None,
            "played_locally": self.played_locally,
        }
        if self.audio_bytes:
            payload["audio_base64"] = base64.b64encode(self.audio_bytes).decode("ascii")
            payload["format"] = self.format or "wav"
        return payload