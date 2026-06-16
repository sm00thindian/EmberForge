"""Pluggable speech-to-text and text-to-speech providers."""

from emberforge.services.voice.base import STTProvider, TTSProvider, TTSResult
from emberforge.services.voice.elevenlabs_tts import ElevenLabsTTS
from emberforge.services.voice.registry import get_device_tts_provider, get_stt_provider, get_tts_provider

__all__ = [
    "STTProvider",
    "TTSProvider",
    "TTSResult",
    "ElevenLabsTTS",
    "get_stt_provider",
    "get_tts_provider",
    "get_device_tts_provider",
]