"""TTS text normalization tests."""

from __future__ import annotations

import json

import pytest

from emberforge.services.voice.tts_text import (
    apply_pronunciations,
    apply_sentence_pauses,
    load_pronunciation_map,
    prepare_tts_text,
)
from emberforge.settings import Settings


@pytest.fixture(autouse=True)
def clear_pronunciation_cache():
    load_pronunciation_map.cache_clear()
    yield
    load_pronunciation_map.cache_clear()


def test_apply_pronunciations_shana_to_shanna():
    text = "When Shana joins us, tell Shana hello."
    result = apply_pronunciations(text, {"Shana": "Shanna"})
    assert result == "When Shanna joins us, tell Shanna hello."


def test_apply_sentence_pauses_between_sentences():
    text = "Yeah, I'm here. What's on your mind?"
    result = apply_sentence_pauses(text, 0.4)
    assert '<break time="0.40s" />' in result
    assert result.startswith("Yeah, I'm here.")
    assert result.endswith("What's on your mind?")


def test_apply_sentence_pauses_skips_when_disabled():
    text = "First. Second."
    assert apply_sentence_pauses(text, 0) == text


def test_apply_pronunciations_preserves_case():
    assert apply_pronunciations("SHANA", {"Shana": "Shanna"}) == "SHANNA"
    assert apply_pronunciations("shana", {"Shana": "Shanna"}) == "shanna"


def test_prepare_tts_text_uses_project_map(test_settings: Settings, tmp_path):
    pron_path = tmp_path / "prompts" / "tts_pronunciations.json"
    pron_path.parent.mkdir(parents=True)
    pron_path.write_text(json.dumps({"Shana": "Shanna"}), encoding="utf-8")

    settings = Settings(
        _env_file=None,
        xai_api_key=test_settings.xai_api_key,
        emberforge_root=str(tmp_path),
    )
    assert prepare_tts_text("Good morning, Shana.", settings) == "Good morning, Shanna."


def test_elevenlabs_speed_validation(monkeypatch):
    from pydantic import ValidationError

    monkeypatch.setenv("ELEVENLABS_SPEED", "2.0")
    with pytest.raises(ValidationError, match="elevenlabs_speed"):
        Settings(_env_file=None, xai_api_key="test")