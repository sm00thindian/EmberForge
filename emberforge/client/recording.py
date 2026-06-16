"""Microphone recording utilities for the Mac voice client."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
CHANNELS = 1
MAX_RECORD_SECONDS = 20
SILENCE_THRESHOLD = 0.012
SILENCE_SECONDS = 1.5
MIN_SPEECH_SECONDS = 0.4


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


def record_until_silence() -> Optional[np.ndarray]:
    print("\nPress ENTER to start listening.")
    input()

    print("Listening... speak now.")
    block_size = int(SAMPLE_RATE * 0.1)
    max_blocks = int(MAX_RECORD_SECONDS / 0.1)
    recorded = []
    speech_started = False
    silent_blocks = 0
    speech_blocks = 0
    silence_blocks_needed = int(SILENCE_SECONDS / 0.1)
    min_speech_blocks = int(MIN_SPEECH_SECONDS / 0.1)

    input_device = resolve_input_device()
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=block_size,
        device=input_device,
    ) as stream:
        for _ in range(max_blocks):
            block, _ = stream.read(block_size)
            block = block[:, 0]
            recorded.append(block)

            energy = float(np.sqrt(np.mean(block**2)))
            if energy >= SILENCE_THRESHOLD:
                speech_started = True
                speech_blocks += 1
                silent_blocks = 0
            elif speech_started:
                silent_blocks += 1
                if silent_blocks >= silence_blocks_needed and speech_blocks >= min_speech_blocks:
                    break

    audio = np.concatenate(recorded)
    if not speech_started or speech_blocks < min_speech_blocks:
        print("No clear speech detected. Try again.")
        return None

    duration = len(audio) / SAMPLE_RATE
    print(f"Captured {duration:.1f}s of audio.")
    return audio