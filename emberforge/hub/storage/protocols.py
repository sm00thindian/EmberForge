"""Storage protocols — local implementations today, AWS backends later."""

from __future__ import annotations

from typing import Protocol

from emberforge.security.device_registry import DeviceRegistry
from emberforge.security.pairing import PairingCodeStore
from emberforge.security.sessions import AdminSessionStore
from emberforge.services.personas import Persona


class ConfigStore(Protocol):
    """Hub configuration secrets and operator-tunable values."""

    @property
    def allows_writes(self) -> bool:
        """Whether setup UI may upsert keys (false for hosted cloud hubs)."""

    def read_values(self) -> dict[str, str]:
        """Return raw key/value pairs for setup snapshots."""

    def upsert(self, updates: dict[str, str]) -> None:
        """Persist configuration updates."""


class ConversationStore(Protocol):
    """Multi-turn memory scoped by session (and tenant via scoped_session_id)."""

    def prepare_messages(
        self,
        session_id: str,
        persona_id: str,
        *,
        clear: bool = False,
    ) -> list[dict[str, str]]: ...

    def record_turn(
        self,
        session_id: str,
        persona_id: str,
        user_message: str,
        assistant_message: str,
    ) -> int: ...

    def turn_count(self, session_id: str) -> int: ...

    def clear(self, session_id: str) -> None: ...

    def reset(self) -> None: ...


class PersonaCatalog(Protocol):
    """Persona definitions and prompt assets."""

    def load(self) -> dict[str, Persona]:
        """Load all personas for this hub instance."""


class SecurityStore(Protocol):
    """Device pairing, admin sessions, and token hashing state."""

    @property
    def salt(self) -> str: ...

    @property
    def device_registry(self) -> DeviceRegistry: ...

    @property
    def pairing_codes(self) -> PairingCodeStore: ...

    @property
    def admin_sessions(self) -> AdminSessionStore: ...