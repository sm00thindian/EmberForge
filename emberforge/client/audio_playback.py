"""Local audio playback for the Mac voice client."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def play_audio_bytes(audio_bytes: bytes, audio_format: str = "mp3") -> None:
    """Play synthesized audio through the Mac speakers."""
    if not audio_bytes:
        return

    if shutil.which("afplay") is None:
        raise RuntimeError("afplay is not available on this system")

    suffix = f".{audio_format.lstrip('.')}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        path = Path(handle.name)
        handle.write(audio_bytes)

    try:
        subprocess.run(["afplay", str(path)], check=False)
    finally:
        path.unlink(missing_ok=True)