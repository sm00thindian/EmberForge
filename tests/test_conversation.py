"""Conversation service tests."""

from __future__ import annotations

from emberforge.services.conversation import format_for_display, voice_to_dict
from emberforge.services.personas import get_persona
from emberforge.settings import Settings


def test_format_for_display_wraps_long_text():
    text = "This is a longer line of text that should be wrapped for a small device screen."
    lines = format_for_display(text, max_lines=3, max_chars_per_line=20)
    assert len(lines) <= 3
    assert all(len(line) <= 21 for line in lines[:-1])


def test_format_for_display_empty():
    assert format_for_display("") == []


def test_voice_to_dict_includes_playback_placeholders(test_settings: Settings):
    ember = get_persona("ember", settings=test_settings)
    voice = voice_to_dict(ember)
    assert voice["provider"] == "elevenlabs"
    assert voice["audio_base64"] is None