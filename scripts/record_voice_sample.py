#!/usr/bin/env python3
"""
Record voice samples for future cloning (with consent).

Usage:
    python scripts/record_voice_sample.py --name kilynn
    python scripts/record_voice_sample.py --name kilynn --duration 15
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_RATE = 24_000
CHANNELS = 1


def voice_dir(name: str) -> Path:
    return ROOT_DIR / "voices" / "custom" / name


def ensure_manifest(name: str, display_name: str | None) -> Path:
    voice_path = voice_dir(name)
    samples_path = voice_path / "samples"
    samples_path.mkdir(parents=True, exist_ok=True)

    manifest_path = voice_path / "manifest.json"
    if not manifest_path.exists():
        template = json.loads(
            (ROOT_DIR / "voices" / "custom" / "_template" / "manifest.json").read_text()
        )
        template["id"] = name
        template["display_name"] = display_name or name.title()
        template["samples_dir"] = f"voices/custom/{name}/samples"
        manifest_path.write_text(json.dumps(template, indent=2) + "\n")

    return samples_path


def next_sample_path(samples_path: Path) -> Path:
    existing = sorted(samples_path.glob("sample_*.wav"))
    index = len(existing) + 1
    return samples_path / f"sample_{index:03d}.wav"


def write_wav(path: Path, audio: np.ndarray) -> None:
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())


def record_sample(duration: float) -> np.ndarray:
    print(f"Recording for {duration:.0f}s... speak clearly and naturally.")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()
    return audio[:, 0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Record voice samples for EmberForge")
    parser.add_argument("--name", required=True, help="Voice profile id (e.g. kilynn)")
    parser.add_argument("--display-name", help="Human-readable voice owner name")
    parser.add_argument("--duration", type=float, default=12.0, help="Seconds per take")
    args = parser.parse_args()

    samples_path = ensure_manifest(args.name, args.display_name)
    manifest_path = voice_dir(args.name) / "manifest.json"

    print("=" * 60)
    print("EmberForge Voice Sample Recorder")
    print("=" * 60)
    print(f"Voice profile: {args.name}")
    print(f"Samples dir:   {samples_path}")
    print()
    print("Only record voices you own or have explicit permission to use.")
    print("Press ENTER to record a take, or type 'done' to finish.")
    print()

    while True:
        cmd = input("> ").strip().lower()
        if cmd in {"done", "quit", "exit", "q"}:
            break
        if cmd not in {"", "record", "r"}:
            print("Press ENTER to record, or type 'done'.")
            continue

        audio = record_sample(args.duration)
        output_path = next_sample_path(samples_path)
        write_wav(output_path, audio)
        print(f"Saved {output_path.name}")

    manifest = json.loads(manifest_path.read_text())
    manifest["last_recorded_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nFinished. Manifest updated at {manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nRecording cancelled.")
        sys.exit(0)