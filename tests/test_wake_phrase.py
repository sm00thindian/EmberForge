"""Wake phrase detection tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.services.personas import load_personas
from emberforge.services.wake_phrase import (
    WakeSessionStore,
    match_wake_phrase,
    normalize_transcript,
    wake_phrases_for_persona,
)
from emberforge.settings import Settings


@pytest.fixture
def converse(test_settings: Settings) -> ConverseService:
    personas = load_personas(test_settings)
    mock_stt = MagicMock()
    mock_stt.available.return_value = True
    return ConverseService(test_settings, personas, stt=mock_stt)


def test_normalize_transcript():
    assert normalize_transcript("  Hey, Ember!  ") == "hey ember"


def test_wake_phrases_for_ember(converse: ConverseService):
    ember = converse.resolve_persona("ember")
    phrases = wake_phrases_for_persona(ember)
    assert "hey ember" in phrases
    assert "hey amber" in phrases


def test_match_wake_phrase_with_command(converse: ConverseService):
    ember = converse.resolve_persona("ember")
    match = match_wake_phrase("Hey Ember, what's the weather?", ember)
    assert match.matched is True
    assert match.command == "what s the weather"
    assert match.phrase == "hey ember"


def test_match_wake_phrase_without_command(converse: ConverseService):
    ember = converse.resolve_persona("ember")
    match = match_wake_phrase("hey ember", ember)
    assert match.matched is True
    assert match.command == ""


def test_match_partial_hey_prefix(converse: ConverseService):
    ember = converse.resolve_persona("ember")
    match = match_wake_phrase("hey", ember)
    assert match.matched is True
    assert match.command == ""


def test_match_embedded_wake_phrase(converse: ConverseService):
    ember = converse.resolve_persona("ember")
    match = match_wake_phrase("um hey ember what time is it", ember)
    assert match.matched is True
    assert "time" in match.command


def test_wake_session_store_ttl():
    store = WakeSessionStore(ttl_seconds=30.0)
    store.arm("device-1", now=100.0)
    assert store.is_armed("device-1", now=120.0) is True
    assert store.is_armed("device-1", now=131.0) is False


@pytest.mark.asyncio
async def test_converse_audio_stt_no_speech_returns_ignored(converse: ConverseService):
    converse.stt.transcribe_wav.side_effect = ValueError("No speech detected in audio")
    result = await converse.converse_audio("ember", b"fake-wav", session_id="device-1")
    assert result.ignored is True


@pytest.mark.asyncio
async def test_converse_audio_ignores_without_wake_phrase(monkeypatch, converse: ConverseService):
    converse.stt.transcribe_wav.return_value = "what is the weather today"
    generate = AsyncMock()
    monkeypatch.setattr("emberforge.services.converse.generate_reply", generate)

    result = await converse.converse_audio(
        "ember",
        b"fake-wav",
        session_id="device-1",
        synthesize_audio=True,
    )

    assert result.ignored is True
    assert result.response_text == ""
    generate.assert_not_called()


@pytest.mark.asyncio
async def test_converse_audio_accepts_wake_phrase(monkeypatch, converse: ConverseService):
    converse.stt.transcribe_wav.return_value = "Hey Ember, what is two plus two?"

    async def fake_generate(persona, message, **kwargs):
        return ConversationResult(
            request_id="req-wake",
            transcript=message,
            response_text="Four",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say"},
            display_lines=["Four"],
            timestamp="2026-06-16T12:00:00+00:00",
            model="grok-3-latest",
        )

    monkeypatch.setattr(
        "emberforge.services.converse.generate_reply",
        AsyncMock(side_effect=fake_generate),
    )

    result = await converse.converse_audio("ember", b"fake-wav", session_id="device-1")
    assert result.ignored is False
    assert result.transcript == "what is two plus two"
    assert result.response_text == "Four"


@pytest.mark.asyncio
async def test_converse_audio_follow_up_without_wake_phrase(monkeypatch, converse: ConverseService):
    converse.wake_sessions.arm("device-1", now=100.0)
    converse.stt.transcribe_wav.return_value = "and what about tomorrow"

    async def fake_generate(persona, message, **kwargs):
        return ConversationResult(
            request_id="req-follow",
            transcript=message,
            response_text="Sunny",
            persona_id=persona.id,
            persona_name=persona.name,
            voice={"provider": "macos_say"},
            display_lines=["Sunny"],
            timestamp="2026-06-16T12:00:00+00:00",
            model="grok-3-latest",
        )

    monkeypatch.setattr(
        "emberforge.services.converse.generate_reply",
        AsyncMock(side_effect=fake_generate),
    )

    monkeypatch.setattr("emberforge.services.wake_phrase.time.monotonic", lambda: 110.0)
    result = await converse.converse_audio("ember", b"fake-wav", session_id="device-1")

    assert result.ignored is False
    assert result.response_text == "Sunny"