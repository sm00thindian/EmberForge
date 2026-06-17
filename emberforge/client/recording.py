"""Microphone recording utilities for the Mac voice client."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
CHANNELS = 1
BLOCK_SECONDS = 0.1

# Push-to-talk limits (Mac dev client)
MAX_RECORD_SECONDS = 30.0
SILENCE_THRESHOLD = 0.012
SILENCE_SECONDS = 1.5
MIN_SPEECH_SECONDS = 0.4
MIN_PRESS_SECONDS = 0.25


def resolve_input_device() -> Optional[int]:
    device_setting = os.getenv("EMBER_INPUT_DEVICE")
    if not device_setting:
        return None
    if device_setting.isdigit():
        return int(device_setting)
    needle = device_setting.lower()
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0 and needle in device["name"].lower():
            return index
    print(f"Could not find input device matching '{device_setting}'. Using system default.")
    return None


def block_energy(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block**2)))


def should_end_on_trailing_silence(
    *,
    speech_started: bool,
    speech_blocks: int,
    silent_blocks: int,
    min_speech_blocks: int,
    silence_blocks_needed: int,
) -> bool:
    """Return True when trailing silence indicates the user finished speaking."""
    return (
        speech_started
        and silent_blocks >= silence_blocks_needed
        and speech_blocks >= min_speech_blocks
    )


def validate_captured_audio(
    audio: np.ndarray,
    *,
    speech_started: bool,
    speech_blocks: int,
    min_speech_blocks: int,
    press_seconds: float,
    min_press_seconds: float = MIN_PRESS_SECONDS,
) -> Optional[np.ndarray]:
    """Discard accidental taps and clips without clear speech."""
    if not speech_started or speech_blocks < min_speech_blocks:
        if press_seconds < min_press_seconds:
            return None
        print("No clear speech detected. Try again.")
        return None
    return audio


def record_while_active(
    is_active: Callable[[], bool],
    *,
    max_seconds: float = MAX_RECORD_SECONDS,
    silence_threshold: float = SILENCE_THRESHOLD,
    silence_seconds: float = SILENCE_SECONDS,
    min_speech_seconds: float = MIN_SPEECH_SECONDS,
    min_press_seconds: float = MIN_PRESS_SECONDS,
    on_listening: Callable[[], None] | None = None,
    on_finished: Callable[[float], None] | None = None,
    input_device: Optional[int] = None,
) -> Optional[np.ndarray]:
    """
    Record while ``is_active()`` is True (push-to-talk hold).

    Stops on key release, trailing silence while still held, or ``max_seconds``.
    """
    if on_listening:
        on_listening()

    block_size = int(SAMPLE_RATE * BLOCK_SECONDS)
    max_blocks = int(max_seconds / BLOCK_SECONDS)
    silence_blocks_needed = int(silence_seconds / BLOCK_SECONDS)
    min_speech_blocks = int(min_speech_seconds / BLOCK_SECONDS)
    recorded: list[np.ndarray] = []
    speech_started = False
    silent_blocks = 0
    speech_blocks = 0
    started_at = time.monotonic()
    device = input_device if input_device is not None else resolve_input_device()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=block_size,
        device=device,
    ) as stream:
        for _ in range(max_blocks):
            if not is_active():
                break

            block, _ = stream.read(block_size)
            block = block[:, 0]
            recorded.append(block)

            energy = block_energy(block)
            if energy >= silence_threshold:
                speech_started = True
                speech_blocks += 1
                silent_blocks = 0
            elif speech_started:
                silent_blocks += 1
                if should_end_on_trailing_silence(
                    speech_started=speech_started,
                    speech_blocks=speech_blocks,
                    silent_blocks=silent_blocks,
                    min_speech_blocks=min_speech_blocks,
                    silence_blocks_needed=silence_blocks_needed,
                ):
                    break

    if not recorded:
        return None

    audio = np.concatenate(recorded)
    press_seconds = time.monotonic() - started_at
    validated = validate_captured_audio(
        audio,
        speech_started=speech_started,
        speech_blocks=speech_blocks,
        min_speech_blocks=min_speech_blocks,
        press_seconds=press_seconds,
        min_press_seconds=min_press_seconds,
    )
    if validated is not None and on_finished:
        duration = len(validated) / SAMPLE_RATE
        on_finished(duration)
    return validated