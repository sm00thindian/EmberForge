"""Runtime platform detection for hub capabilities."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def runtime_platform() -> str:
    """OS identifier (e.g. darwin, linux)."""
    return sys.platform


def running_in_container() -> bool:
    """True when the process appears to run inside Docker/Podman."""
    return Path("/.dockerenv").is_file() or Path("/run/.containerenv").is_file()


def macos_say_available() -> bool:
    """True when the hub can invoke macOS ``say`` for ``play_audio``."""
    return sys.platform == "darwin" and shutil.which("say") is not None