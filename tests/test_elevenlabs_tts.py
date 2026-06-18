"""ElevenLabs TTS provider tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.elevenlabs_tts import ElevenLabsTTS
from emberforge.services.voice.profiles import load_voice_profile
from emberforge.services.voice.registry import get_device_tts_provider
from emberforge.settings import Settings


@pytest.fixture
def eleven_settings(monkeypatch, test_settings: Settings) -> Settings:
    from emberforge.services.voice.tts_text import load_pronunciation_map
    from emberforge.settings import get_settings

    load_pronunciation_map.cache_clear()
    monkeypatch.setenv("XAI_API_KEY", test_settings.xai_api_key)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven-key")
    monkeypatch.setenv("ELEVENLABS_DEFAULT_VOICE_ID", "default-voice-123")
    get_settings.cache_clear()
    return Settings()


@pytest.mark.asyncio
async def test_elevenlabs_synthesize_applies_pronunciations_and_speed(eleven_settings: Settings, monkeypatch):
    import httpx

    captured: dict = {}

    async def fake_post_with_retry(client, url, **kwargs):
        captured.update(kwargs)
        return httpx.Response(200, content=b"mp3")

    monkeypatch.setattr("emberforge.services.voice.elevenlabs_tts.post_with_retry", fake_post_with_retry)

    tts = ElevenLabsTTS(eleven_settings)
    voice = VoiceConfig(provider="elevenlabs", voice="voice-abc")
    result = await tts.synthesize("Hello Shana. Welcome back.", voice)

    payload = captured["json"]
    assert payload["voice_settings"]["speed"] == pytest.approx(0.9)
    assert "Hello Shanna" in payload["text"]
    assert "Welcome back." in payload["text"]
    assert '<break time="0.40s" />' in payload["text"]
    assert result.audio_bytes == b"mp3"


@pytest.mark.asyncio
async def test_elevenlabs_synthesize_returns_mp3(eleven_settings: Settings):
    tts = ElevenLabsTTS(eleven_settings)
    voice = VoiceConfig(provider="elevenlabs", voice="voice-abc")

    with patch.object(
        tts,
        "_fetch_audio",
        AsyncMock(return_value=b"fake-mp3-bytes"),
    ):
        result = await tts.synthesize("Hello from Ember", voice)

    assert result.format == "mp3"
    assert result.audio_bytes == b"fake-mp3-bytes"
    payload = result.to_voice_dict()
    assert payload["audio_base64"] is not None
    assert payload["format"] == "mp3"


@pytest.mark.asyncio
async def test_elevenlabs_without_api_key_returns_metadata_only(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    monkeypatch.delenv("ELEVENLABS_DEFAULT_VOICE_ID", raising=False)
    settings = Settings(_env_file=None)
    tts = ElevenLabsTTS(settings)
    voice = VoiceConfig(provider="elevenlabs", voice="voice-abc")
    result = await tts.synthesize("Hello", voice)
    assert result.audio_bytes is None


def test_device_tts_fallback_for_macos_say_persona(eleven_settings: Settings):
    voice = VoiceConfig(provider="macos_say", voice="Samantha")
    provider, resolved_voice = get_device_tts_provider(voice, eleven_settings)
    assert provider.produces_audio() is True
    assert resolved_voice.voice == "default-voice-123"


def test_voice_profile_from_manifest(test_settings: Settings, tmp_path):
    profile_dir = tmp_path / "voices" / "custom" / "kilynn"
    profile_dir.mkdir(parents=True)
    (profile_dir / "manifest.json").write_text(
        """
        {
          "id": "kilynn",
          "display_name": "Kilynn",
          "provider": "recorded",
          "status": "ready",
          "consent": {"permission_granted": true},
          "elevenlabs_voice_id": "clone-voice-999"
        }
        """
    )

    load_voice_profile.cache_clear()
    profile = load_voice_profile("kilynn", str(tmp_path))
    assert profile is not None
    assert profile.ready_for_synthesis is True
    assert profile.elevenlabs_voice_id == "clone-voice-999"