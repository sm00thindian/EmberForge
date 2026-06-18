"""Mac voice client tests."""

from __future__ import annotations

import base64
from unittest.mock import patch

import pytest

from emberforge.client import mac_voice
from emberforge.client.mac_voice import parse_quoted_prompt, speak_response


def test_parse_quoted_prompt_double_quotes():
    assert parse_quoted_prompt('"Hal, close the cabin doors"') == "Hal, close the cabin doors"


def test_parse_quoted_prompt_single_quotes():
    assert parse_quoted_prompt("'Open the pod bay doors'") == "Open the pod bay doors"


def test_parse_quoted_prompt_ignores_commands():
    assert parse_quoted_prompt("persona hal_9000") is None
    assert parse_quoted_prompt("") is None
    assert parse_quoted_prompt('""') is None


def test_parse_quoted_prompt_preserves_case():
    assert parse_quoted_prompt('"Hello HAL"') == "Hello HAL"


def test_use_backend_tts_when_elevenlabs_mode(monkeypatch):
    monkeypatch.setenv("EMBER_MAC_TTS", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_DEFAULT_VOICE_ID", "voice-123")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    mac_voice._settings = mac_voice.Settings()
    assert mac_voice._use_backend_tts() is True


def test_speak_response_plays_backend_audio_base64():
    audio = base64.b64encode(b"fake-mp3").decode("ascii")
    with patch("emberforge.client.mac_voice.play_audio_bytes") as play:
        speak_response("Hello", {"audio_base64": audio, "format": "mp3"})
    play.assert_called_once_with(b"fake-mp3", "mp3")