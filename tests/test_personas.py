"""Persona loading tests."""

from __future__ import annotations

import pytest

from emberforge.services.personas import get_persona, load_personas
from emberforge.settings import Settings


def test_load_builtin_personas(test_settings: Settings):
    personas = load_personas(test_settings)
    assert "ember" in personas
    assert "hal_9000" in personas


def test_ember_has_system_prompt(test_settings: Settings):
    ember = get_persona("ember", settings=test_settings)
    assert "Ember" in ember.system_prompt
    assert ember.voice.provider == "elevenlabs"


def test_hal_device_dict(test_settings: Settings):
    hal = get_persona("hal_9000", settings=test_settings)
    device_view = hal.to_device_dict()
    assert device_view["id"] == "hal_9000"
    assert "inspired_by" in device_view


def test_unknown_persona_raises(test_settings: Settings):
    with pytest.raises(KeyError, match="Unknown persona"):
        get_persona("not_a_real_persona", settings=test_settings)