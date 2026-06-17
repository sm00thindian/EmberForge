"""Persisted registry of paired device tokens."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from emberforge.security.tokens import generate_token, hash_token, verify_token


@dataclass(frozen=True)
class PairedDevice:
    device_id: str
    name: str
    paired_at: str


class DeviceRegistry:
    def __init__(self, path: Path, *, salt: str) -> None:
        self._path = path
        self._salt = salt
        self._devices: dict[str, dict] = {}
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        if not self._path.exists():
            self._devices = {}
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._devices = data.get("devices", {})

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"devices": self._devices}
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def has_devices(self) -> bool:
        return bool(self._devices)

    def list_devices(self) -> list[PairedDevice]:
        return [
            PairedDevice(
                device_id=device_id,
                name=entry.get("name", device_id),
                paired_at=entry.get("paired_at", ""),
            )
            for device_id, entry in sorted(self._devices.items())
        ]

    def pair_device(self, *, device_id: str, name: str | None = None) -> str:
        token = generate_token(32)
        token_hash = hash_token(token, salt=self._salt)
        self._devices[device_id] = {
            "token_hash": token_hash,
            "name": name or device_id,
            "paired_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        return token

    def verify_device_token(self, token: str) -> str | None:
        for device_id, entry in self._devices.items():
            token_hash = entry.get("token_hash", "")
            if verify_token(token, token_hash, salt=self._salt):
                return device_id
        return None

    def revoke_device(self, device_id: str) -> bool:
        if device_id not in self._devices:
            return False
        del self._devices[device_id]
        self._save()
        return True


def load_or_create_salt(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    salt = secrets.token_hex(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(salt, encoding="utf-8")
    return salt