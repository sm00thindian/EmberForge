"""Filesystem layout for a single-tenant maker hub (portable to object stores later)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from emberforge.settings import Settings


@dataclass(frozen=True)
class ProjectLayout:
    """
    Resolved content and state paths for one hub instance.

    Today this maps to a clone directory (personas/, prompts/, .env).
    A hosted deployment can implement the same interface with tenant-prefixed
    object keys without changing conversation or device APIs.
    """

    root: Path
    tenant_key: str = ""

    @classmethod
    def from_settings(cls, settings: Settings, *, tenant_key: str = "") -> ProjectLayout:
        return cls(root=settings.project_root, tenant_key=tenant_key)

    @property
    def personas_dir(self) -> Path:
        return self.root / "personas"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"

    @property
    def voices_dir(self) -> Path:
        return self.root / "voices"

    @property
    def env_file(self) -> Path:
        return self.root / ".env"

    @property
    def security_state_dir(self) -> Path:
        return self.root / ".emberforge"

    def resolve_relative(self, relative_path: str) -> Path:
        return self.root / relative_path