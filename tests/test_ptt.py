"""Push-to-talk session tests."""

from __future__ import annotations

import time
from unittest.mock import patch

import numpy as np
import pytest
from pynput import keyboard

from emberforge.client.ptt import (
    PushToTalkSession,
    SessionEventType,
    is_typing_key,
    keys_equal,
    ptt_key_virtual_codes,
    resolve_ptt_key,
    should_suppress_ptt_vk,
)


def test_resolve_ptt_key_aliases():
    assert resolve_ptt_key("space") == keyboard.Key.space
    assert resolve_ptt_key("f5") == keyboard.Key.f5


def test_resolve_ptt_key_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported PTT key"):
        resolve_ptt_key("not-a-real-key-name")


def test_keys_equal_matches_vk_aliases():
    observed = keyboard.KeyCode.from_vk(49)
    assert keys_equal(observed, keyboard.Key.space)


def test_ptt_key_label():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    assert session.ptt_key_label == "SPACE"


def test_enter_press_queues_command_event():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session._on_press(keyboard.Key.enter)
    event = session.wait_event(timeout=1.0)
    assert event is not None
    assert event.type == SessionEventType.COMMAND


def test_hold_records_and_emits_audio_event():
    audio = np.full(16_000, 0.02, dtype=np.float32)
    session = PushToTalkSession(ptt_key=keyboard.Key.space)

    with patch("emberforge.client.ptt.record_while_active", return_value=audio) as record:
        session._on_press(keyboard.Key.space)
        session._on_release(keyboard.Key.space)
        event = session.wait_event(timeout=2.0)

    record.assert_called_once()
    assert event is not None
    assert event.type == SessionEventType.AUDIO
    assert event.audio is audio
    assert not session.is_recording


def test_recording_thread_clears_stuck_hold_state():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session._held.set()

    with patch("emberforge.client.ptt.record_while_active", return_value=None):
        session._start_recording()
        deadline = time.monotonic() + 2.0
        while session.is_recording and time.monotonic() < deadline:
            time.sleep(0.01)

    assert not session.is_recording
    assert not session._held.is_set()


def test_is_typing_key_detects_printable_characters():
    assert is_typing_key(keyboard.KeyCode.from_char('"'))
    assert not is_typing_key(keyboard.Key.space)
    assert not is_typing_key(keyboard.Key.shift)


def test_typing_enters_command_mode_and_queues_event():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session._on_press(keyboard.KeyCode.from_char('"'))
    assert session.command_mode
    event = session.wait_event(timeout=1.0)
    assert event is not None
    assert event.type == SessionEventType.TYPING


def test_space_while_typing_does_not_start_recording():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session.enter_command_mode()

    with patch("emberforge.client.ptt.record_while_active") as record:
        session._on_press(keyboard.Key.space)

    record.assert_not_called()


def test_command_mode_ignores_ptt_press():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session.enter_command_mode()

    with patch("emberforge.client.ptt.record_while_active") as record:
        session._on_press(keyboard.Key.space)
        session._on_release(keyboard.Key.space)

    record.assert_not_called()


def test_ptt_key_virtual_codes_for_space():
    assert 49 in ptt_key_virtual_codes(keyboard.Key.space)


def test_should_suppress_ptt_vk_only_outside_command_mode():
    ptt_vks = ptt_key_virtual_codes(keyboard.Key.space)
    assert should_suppress_ptt_vk(command_mode=False, vk=49, ptt_vks=ptt_vks)
    assert not should_suppress_ptt_vk(command_mode=True, vk=49, ptt_vks=ptt_vks)
    assert not should_suppress_ptt_vk(command_mode=False, vk=36, ptt_vks=ptt_vks)


def test_listener_uses_selective_suppress_not_global():
    session = PushToTalkSession(ptt_key=keyboard.Key.space)
    session.start()
    assert session._listener is not None
    assert session._listener.suppress is False
    if __import__("sys").platform == "darwin":
        assert callable(session._listener._options.get("intercept"))
    session.stop()