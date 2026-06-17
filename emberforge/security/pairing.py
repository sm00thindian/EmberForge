"""Short-lived pairing codes for registering new devices."""

from __future__ import annotations

import secrets
import string
import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class PairingCode:
    code: str
    expires_at: float


class PairingCodeStore:
    def __init__(self, *, ttl_seconds: float = 300.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._codes: dict[str, float] = {}
        self._lock = Lock()

    def issue(self) -> PairingCode:
        alphabet = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._purge_locked(time.time())
            self._codes[code] = expires_at
        return PairingCode(code=code, expires_at=expires_at)

    def consume(self, code: str) -> bool:
        normalized = code.strip().upper().replace(" ", "")
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            expires_at = self._codes.get(normalized)
            if expires_at is None:
                return False
            if expires_at <= now:
                self._codes.pop(normalized, None)
                return False
            del self._codes[normalized]
            return True

    def _purge_locked(self, now: float) -> None:
        expired = [key for key, expires in self._codes.items() if expires <= now]
        for key in expired:
            self._codes.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._codes.clear()