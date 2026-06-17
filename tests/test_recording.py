"""Recording helper tests."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from emberforge.client.recording import (
    MIN_PRESS_SECONDS,
    block_energy,
    record_while_active,
    should_end_on_trailing_silence,
    validate_captured_audio,
)


def test_block_energy_detects_signal():
    loud = np.full(1600, 0.05, dtype=np.float32)
    quiet = np.zeros(1600, dtype=np.float32)
    assert block_energy(loud) > block_energy(quiet)


def test_should_end_on_trailing_silence_requires_minimum_speech():
    assert not should_end_on_trailing_silence(
        speech_started=True,
        speech_blocks=1,
        silent_blocks=20,
        min_speech_blocks=4,
        silence_blocks_needed=15,
    )
    assert should_end_on_trailing_silence(
        speech_started=True,
        speech_blocks=5,
        silent_blocks=15,
        min_speech_blocks=4,
        silence_blocks_needed=15,
    )


def test_validate_captured_audio_discards_short_empty_press():
    audio = np.zeros(1600, dtype=np.float32)
    assert (
        validate_captured_audio(
            audio,
            speech_started=False,
            speech_blocks=0,
            min_speech_blocks=4,
            press_seconds=MIN_PRESS_SECONDS / 2,
        )
        is None
    )


def test_validate_captured_audio_accepts_clear_speech():
    audio = np.full(16_000, 0.02, dtype=np.float32)
    result = validate_captured_audio(
        audio,
        speech_started=True,
        speech_blocks=8,
        min_speech_blocks=4,
        press_seconds=1.0,
    )
    assert result is audio


class _FakeStream:
    def __init__(self, blocks: list[np.ndarray]) -> None:
        self._blocks = blocks
        self._index = 0

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self, block_size: int):
        if self._index >= len(self._blocks):
            block = np.zeros(block_size, dtype=np.float32)
        else:
            block = self._blocks[self._index]
            self._index += 1
        return block.reshape(-1, 1), None


def _speech_block(block_size: int = 1600) -> np.ndarray:
    return np.full(block_size, 0.05, dtype=np.float32)


def _quiet_block(block_size: int = 1600) -> np.ndarray:
    return np.zeros(block_size, dtype=np.float32)


def test_record_while_active_stops_on_release():
    blocks = [_speech_block()] * 5
    active_calls = {"count": 0}

    def is_active() -> bool:
        active_calls["count"] += 1
        return active_calls["count"] <= 5

    with patch("emberforge.client.recording.sd.InputStream", return_value=_FakeStream(blocks)):
        audio = record_while_active(is_active, input_device=0)

    assert audio is not None
    assert len(audio) == 8000


def test_record_while_active_stops_on_trailing_silence_while_held():
    blocks = [_speech_block()] * 6 + [_quiet_block()] * 20
    with patch("emberforge.client.recording.sd.InputStream", return_value=_FakeStream(blocks)):
        audio = record_while_active(lambda: True, input_device=0)

    assert audio is not None
    # Six speech blocks plus 1.5s (15 blocks) of trailing silence.
    assert len(audio) == 21 * 1600