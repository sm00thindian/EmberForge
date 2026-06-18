"""Maker-local storage backends (filesystem + in-process memory)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from emberforge.config.env_file import read_env_values, update_env_file
from emberforge.security.device_registry import DeviceRegistry, load_or_create_salt
from emberforge.security.pairing import PairingCodeStore
from emberforge.security.sessions import AdminSessionStore
from emberforge.services.personas import Persona, load_personas
from emberforge.settings import Settings


class ConfigWriteDisabledError(RuntimeError):
    """Raised when a hosted deployment profile blocks .env mutations."""


class LocalConfigStore:
    """Read/write hub configuration via the project `.env` file."""

    def __init__(self, path: Path, *, allows_writes: bool = True) -> None:
        self._path = path
        self._allows_writes = allows_writes

    @property
    def path(self) -> Path:
        return self._path

    @property
    def allows_writes(self) -> bool:
        return self._allows_writes

    def read_values(self) -> dict[str, str]:
        return read_env_values(self._path)

    def upsert(self, updates: dict[str, str]) -> None:
        if not self._allows_writes:
            raise ConfigWriteDisabledError(
                "Configuration file writes are disabled for this deployment profile"
            )
        update_env_file(self._path, updates)


class LocalPersonaCatalog:
    """Load personas from `personas/*.json` and `prompts/` on disk."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def load(self) -> dict[str, Persona]:
        return load_personas(self._settings)


@dataclass
class LocalSecurityStore:
    """Filesystem-backed pairing registry under `.emberforge/`."""

    salt: str
    device_registry: DeviceRegistry
    pairing_codes: PairingCodeStore
    admin_sessions: AdminSessionStore

    def as_dict(self) -> dict[str, object]:
        """Backward-compatible shape for legacy `get_security_state()` callers."""
        return {
            "salt": self.salt,
            "device_registry": self.device_registry,
            "pairing_codes": self.pairing_codes,
            "admin_sessions": self.admin_sessions,
        }


def build_local_security_store(settings: Settings, state_dir: Path) -> LocalSecurityStore:
    salt = load_or_create_salt(state_dir / "salt")
    return LocalSecurityStore(
        salt=salt,
        device_registry=DeviceRegistry(state_dir / "devices.json", salt=salt),
        pairing_codes=PairingCodeStore(ttl_seconds=settings.pairing_code_ttl_seconds),
        admin_sessions=AdminSessionStore(
            salt=salt,
            ttl_seconds=settings.admin_session_ttl_seconds,
        ),
    )