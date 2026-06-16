"""Voice provider tests."""

from __future__ import annotations

import pytest

from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.mac_say_tts import MacSayTTS
from emberforge.services.voice.registry import (
    get_mac_tts_provider,
    get_stt_provider,
    get_tts_provider,
    resolve_mac_tts_mode,
)
from emberforge.services.voice.stub_tts import StubTTS
from emberforge.services.voice.whisper_stt import WhisperSTT
from emberforge.settings import Settings


def test_whisper_stt_available():
    stt = WhisperSTT(Settings())
    assert stt.name == "whisper"
    assert stt.available() is True


def test_get_stt_provider_returns_whisper(test_settings: Settings):
    stt = get_stt_provider(test_settings)
    assert isinstance(stt, WhisperSTT)


def test_get_tts_provider_macos_say():
    voice = VoiceConfig(provider="macos_say", voice="Samantha", rate=180)
    tts = get_tts_provider(voice)
    assert isinstance(tts, MacSayTTS)


def test_get_tts_provider_elevenlabs_clone():
    from emberforge.services.voice.elevenlabs_tts import ElevenLabsTTS

    voice = VoiceConfig(provider="elevenlabs_clone", profile="kilynn")
    tts = get_tts_provider(voice)
    assert isinstance(tts, ElevenLabsTTS)


def test_mac_tts_defaults_to_macos_say(test_settings: Settings):
    voice = VoiceConfig(provider="macos_say", voice="Shelley (English (US))", rate=155)
    tts, resolved_voice = get_mac_tts_provider(voice, test_settings)
    assert isinstance(tts, MacSayTTS)
    assert resolved_voice.voice == "Shelley (English (US))"


def test_mac_tts_elevenlabs_mode(monkeypatch, test_settings: Settings):
    from emberforge.settings import get_settings

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven-key")
    monkeypatch.setenv("ELEVENLABS_DEFAULT_VOICE_ID", "voice-123")
    monkeypatch.setenv("EMBER_MAC_TTS", "elevenlabs")
    get_settings.cache_clear()
    settings = Settings()

    voice = VoiceConfig(provider="macos_say", voice="Shelley (English (US))")
    tts, resolved_voice = get_mac_tts_provider(voice, settings)
    from emberforge.services.voice.elevenlabs_tts import ElevenLabsTTS

    assert isinstance(tts, ElevenLabsTTS)
    assert resolved_voice.voice == "voice-123"


def test_resolve_mac_tts_auto_falls_back_without_elevenlabs(monkeypatch, test_settings: Settings):
    from emberforge.settings import get_settings

    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    monkeypatch.setenv("ELEVENLABS_DEFAULT_VOICE_ID", "")
    monkeypatch.setenv("EMBER_MAC_TTS", "auto")
    get_settings.cache_clear()
    settings = Settings()
    assert resolve_mac_tts_mode(settings) == "macos_say"


@pytest.mark.asyncio
async def test_tts_result_from_voice_config():
    from emberforge.services.voice.base import TTSResult

    voice = VoiceConfig(provider="macos_say", voice="Daniel", rate=160)
    result = TTSResult.from_voice_config(voice)
    payload = result.to_voice_dict()
    assert payload["provider"] == "macos_say"
    assert payload["voice"] == "Daniel"
    assert payload["audio_base64"] is None