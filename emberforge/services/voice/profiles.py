"""Load custom voice profiles from voices/custom/<profile>/manifest.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from emberforge.settings import Settings, get_settings


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    display_name: str
    provider: str
    status: str
    elevenlabs_voice_id: str | None
    consent_granted: bool
    manifest_path: Path

    @property
    def ready_for_synthesis(self) -> bool:
        return bool(self.elevenlabs_voice_id) and self.consent_granted


def _load_manifest(path: Path) -> VoiceProfile:
    data = json.loads(path.read_text(encoding="utf-8"))
    consent = data.get("consent", {})
    return VoiceProfile(
        id=data["id"],
        display_name=data.get("display_name", data["id"]),
        provider=data.get("provider", "recorded"),
        status=data.get("status", "unknown"),
        elevenlabs_voice_id=data.get("elevenlabs_voice_id"),
        consent_granted=bool(consent.get("permission_granted")),
        manifest_path=path,
    )


@lru_cache
def load_voice_profile(profile_id: str, project_root: str) -> VoiceProfile | None:
    root = Path(project_root)
    manifest_path = root / "voices" / "custom" / profile_id / "manifest.json"
    if not manifest_path.exists():
        return None
    return _load_manifest(manifest_path)


def get_voice_profile(profile_id: str, settings: Settings | None = None) -> VoiceProfile | None:
    resolved = settings or get_settings()
    return load_voice_profile(profile_id, str(resolved.project_root))