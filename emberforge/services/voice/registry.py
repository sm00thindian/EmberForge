"""Factory for STT and TTS providers."""

from __future__ import annotations

from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.base import STTProvider, TTSProvider
from emberforge.services.voice.elevenlabs_tts import ElevenLabsTTS
from emberforge.services.voice.mac_say_tts import MacSayTTS
from emberforge.services.voice.stub_tts import StubTTS
from emberforge.services.voice.whisper_stt import WhisperSTT
from emberforge.settings import Settings, get_settings

_stt_singleton: WhisperSTT | None = None
_stt_model: str | None = None
_elevenlabs_singleton: ElevenLabsTTS | None = None
_elevenlabs_api_key: str | None = None


def get_stt_provider(settings: Settings | None = None) -> STTProvider:
    global _stt_singleton, _stt_model
    resolved = settings or get_settings()
    if _stt_singleton is None or _stt_model != resolved.whisper_model:
        _stt_singleton = WhisperSTT(resolved)
        _stt_model = resolved.whisper_model
    return _stt_singleton


def _get_elevenlabs_tts(settings: Settings) -> ElevenLabsTTS:
    global _elevenlabs_singleton, _elevenlabs_api_key
    api_key = settings.elevenlabs_api_key
    if _elevenlabs_singleton is None or _elevenlabs_api_key != api_key:
        _elevenlabs_singleton = ElevenLabsTTS(settings)
        _elevenlabs_api_key = api_key
    return _elevenlabs_singleton


def get_tts_provider(voice: VoiceConfig, settings: Settings | None = None) -> TTSProvider:
    resolved = settings or get_settings()
    provider_name = voice.provider or "macos_say"

    if provider_name in {"elevenlabs", "elevenlabs_clone"}:
        return _get_elevenlabs_tts(resolved)

    if provider_name == "macos_say":
        return MacSayTTS()

    if provider_name == "recorded":
        return StubTTS("recorded")

    return StubTTS(provider_name)


def get_device_tts_provider(
    voice: VoiceConfig,
    settings: Settings | None = None,
) -> tuple[TTSProvider, VoiceConfig]:
    """
    Resolve TTS for consumer devices.

    Uses the persona voice when it produces audio; otherwise falls back to
    ElevenLabs default voice when configured.
    """
    resolved = settings or get_settings()
    primary = get_tts_provider(voice, resolved)
    if primary.produces_audio():
        return primary, voice

    if (
        resolved.device_tts_fallback
        and resolved.server_tts_available
        and resolved.elevenlabs_default_voice_id
    ):
        fallback_voice = VoiceConfig(
            provider="elevenlabs",
            voice=resolved.elevenlabs_default_voice_id,
        )
        return _get_elevenlabs_tts(resolved), fallback_voice

    return primary, voice


def resolve_mac_tts_mode(settings: Settings) -> str:
    """Resolve the effective Mac TTS mode from settings."""
    mode = settings.mac_tts_mode
    if mode == "auto":
        return "elevenlabs" if settings.mac_elevenlabs_ready else "macos_say"
    if mode == "elevenlabs" and not settings.mac_elevenlabs_ready:
        return "macos_say"
    return mode


def get_mac_tts_provider(
    voice: VoiceConfig,
    settings: Settings | None = None,
) -> tuple[TTSProvider, VoiceConfig]:
    """
    Resolve TTS for the Mac voice companion.

    Default is macOS `say`. Per-session mode is set by start_ember.sh
    (EMBER_MAC_TTS exported for this run only).
    """
    resolved = settings or get_settings()
    mode = resolve_mac_tts_mode(resolved)

    if mode == "elevenlabs":
        return get_device_tts_provider(voice, resolved)

    return get_tts_provider(voice, resolved), voice