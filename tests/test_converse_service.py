"""ConverseService tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from emberforge.errors import EmberForgeError
from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.services.personas import load_personas
from emberforge.settings import Settings


@pytest.fixture
def converse(test_settings: Settings) -> ConverseService:
    personas = load_personas(test_settings)
    mock_stt = MagicMock()
    mock_stt.available.return_value = True
    mock_stt.transcribe_wav.return_value = "hello from audio"
    return ConverseService(test_settings, personas, stt=mock_stt)


@pytest.mark.asyncio
async def test_converse_text(monkeypatch, converse: ConverseService):
    async def fake_generate(persona, message, **kwargs):
        return ConversationResult(
            request_id="req-1",
            transcript=message,
            response_text="Hello back",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say"},
            display_lines=["Hello back"],
            timestamp="2026-06-16T12:00:00+00:00",
        )

    monkeypatch.setattr(
        "emberforge.services.converse.generate_reply",
        AsyncMock(side_effect=fake_generate),
    )

    result = await converse.converse_text("ember", "Hi Ember")
    assert result.transcript == "Hi Ember"
    assert result.response_text == "Hello back"
    assert result.voice["provider"] == "macos_say"
    assert result.voice["voice"] == "Shelley (English (US))"


@pytest.mark.asyncio
async def test_converse_text_synthesize_audio(monkeypatch, converse: ConverseService):
    async def fake_generate(persona, message, **kwargs):
        return ConversationResult(
            request_id="req-3",
            transcript=message,
            response_text="Device audio reply",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say"},
            display_lines=["Device audio reply"],
            timestamp="2026-06-16T12:00:00+00:00",
        )

    async def fake_synthesize(text, voice):
        from emberforge.services.voice.base import TTSResult

        return TTSResult(
            provider="elevenlabs",
            voice="default-voice",
            format="mp3",
            audio_bytes=b"mp3data",
        )

    monkeypatch.setattr(
        "emberforge.services.converse.generate_reply",
        AsyncMock(side_effect=fake_generate),
    )

    mock_tts = AsyncMock()
    mock_tts.produces_audio = lambda: True
    mock_tts.synthesize = fake_synthesize
    monkeypatch.setattr(
        "emberforge.services.converse.get_device_tts_provider",
        lambda voice, settings: (mock_tts, voice),
    )

    result = await converse.converse_text("ember", "Hi", synthesize_audio=True)
    assert result.voice["audio_base64"] is not None
    assert result.voice["format"] == "mp3"


@pytest.mark.asyncio
async def test_converse_audio(monkeypatch, converse: ConverseService):
    async def fake_generate(persona, message, **kwargs):
        return ConversationResult(
            request_id="req-2",
            transcript=message,
            response_text="Audio reply",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say"},
            display_lines=["Audio reply"],
            timestamp="2026-06-16T12:00:00+00:00",
        )

    monkeypatch.setattr(
        "emberforge.services.converse.generate_reply",
        AsyncMock(side_effect=fake_generate),
    )

    result = await converse.converse_audio("hal_9000", b"fake-wav")
    assert result.transcript == "hello from audio"
    assert result.persona_id == "hal_9000"
    converse.stt.transcribe_wav.assert_called_once_with(b"fake-wav")


def test_resolve_unknown_persona(converse: ConverseService):
    with pytest.raises(EmberForgeError) as exc_info:
        converse.resolve_persona("not_real")
    assert exc_info.value.code == "PERSONA_NOT_FOUND"