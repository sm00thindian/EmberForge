"""Load and resolve EmberForge personas (personality + voice config)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from emberforge.settings import Settings, get_settings


@dataclass(frozen=True)
class VoiceConfig:
    provider: str
    voice: str | None = None
    rate: int | None = None
    profile: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceConfig:
        return cls(
            provider=data.get("provider", "macos_say"),
            voice=data.get("voice"),
            rate=data.get("rate"),
            profile=data.get("profile"),
        )


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    tagline: str
    system_prompt: str
    voice: VoiceConfig
    temperature: float
    type: str
    inspired_by: str | None = None
    disclaimer: str | None = None

    def to_device_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "type": self.type,
        }
        if self.inspired_by:
            payload["inspired_by"] = self.inspired_by
        return payload

    def to_public_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "type": self.type,
            "voice": {
                "provider": self.voice.provider,
                "voice": self.voice.voice,
                "rate": self.voice.rate,
                "profile": self.voice.profile,
            },
            "temperature": self.temperature,
        }
        if self.inspired_by:
            payload["inspired_by"] = self.inspired_by
        if self.disclaimer:
            payload["disclaimer"] = self.disclaimer
        return payload


def _read_prompt(project_root: Path, prompt_file: str) -> str:
    path = project_root / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Persona prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_persona_file(path: Path, project_root: Path) -> Persona:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Persona(
        id=data["id"],
        name=data["name"],
        tagline=data.get("tagline", ""),
        system_prompt=_read_prompt(project_root, data["prompt_file"]),
        voice=VoiceConfig.from_dict(data.get("voice", {})),
        temperature=float(data.get("temperature", 0.7)),
        type=data.get("type", "companion"),
        inspired_by=data.get("inspired_by"),
        disclaimer=data.get("disclaimer"),
    )


def load_personas(settings: Settings | None = None) -> dict[str, Persona]:
    resolved = settings or get_settings()
    personas_dir = resolved.personas_dir
    personas: dict[str, Persona] = {}

    for path in sorted(personas_dir.glob("*.json")):
        persona = _load_persona_file(path, resolved.project_root)
        personas[persona.id] = persona

    if resolved.default_persona_id not in personas:
        raise RuntimeError(
            f"Default persona '{resolved.default_persona_id}' is missing from {personas_dir}"
        )
    return personas


def get_persona(
    persona_id: str,
    personas: dict[str, Persona] | None = None,
    settings: Settings | None = None,
) -> Persona:
    registry = personas or load_personas(settings)
    if persona_id not in registry:
        available = ", ".join(sorted(registry))
        raise KeyError(f"Unknown persona '{persona_id}'. Available: {available}")
    return registry[persona_id]