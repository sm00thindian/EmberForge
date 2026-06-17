"""Application-wide security singletons."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from emberforge.security.device_registry import DeviceRegistry, load_or_create_salt
from emberforge.security.pairing import PairingCodeStore
from emberforge.security.sessions import AdminSessionStore
from emberforge.settings import get_settings


@lru_cache
def get_security_state() -> dict:
    resolved = get_settings()
    state_dir = resolved.security_state_dir
    salt = load_or_create_salt(state_dir / "salt")
    return {
        "salt": salt,
        "device_registry": DeviceRegistry(state_dir / "devices.json", salt=salt),
        "pairing_codes": PairingCodeStore(ttl_seconds=resolved.pairing_code_ttl_seconds),
        "admin_sessions": AdminSessionStore(
            salt=salt,
            ttl_seconds=resolved.admin_session_ttl_seconds,
        ),
    }


def reset_security_state() -> None:
    get_security_state.cache_clear()


def security_state_dir_for(root: Path) -> Path:
    return root / ".emberforge"