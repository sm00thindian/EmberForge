"""Backward-compatible STT helpers — prefer emberforge.services.voice."""

from __future__ import annotations

from emberforge.services.voice.registry import get_stt_provider
from emberforge.settings import Settings, get_settings


def transcribe_wav(audio_bytes: bytes, settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return get_stt_provider(resolved).transcribe_wav(audio_bytes)


def stt_available() -> bool:
    return get_stt_provider().available()