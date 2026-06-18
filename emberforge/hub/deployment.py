"""Deployment profiles for maker-local vs future hosted cloud hubs."""

from __future__ import annotations

from enum import Enum


class DeploymentProfile(str, Enum):
    """Where and how this hub process is expected to run."""

    LOCAL = "local"
    DOCKER = "docker"
    CLOUD = "cloud"

    @classmethod
    def from_value(cls, value: str) -> DeploymentProfile:
        normalized = value.strip().lower()
        for profile in cls:
            if profile.value == normalized:
                return profile
        raise ValueError(
            f"ember_deployment must be one of: {', '.join(p.value for p in cls)}"
        )

    @property
    def is_maker_hosted(self) -> bool:
        """True when the operator runs the hub on their own machine or LAN."""
        return self in {DeploymentProfile.LOCAL, DeploymentProfile.DOCKER}

    @property
    def allows_env_file_writes(self) -> bool:
        """Setup UI may upsert keys into a host .env file."""
        return self.is_maker_hosted

    @property
    def localhost_setup_mutations(self) -> bool:
        """Setup writes restricted to localhost in production (M7)."""
        return self.is_maker_hosted

    @property
    def state_backend(self) -> str:
        """Logical persistence backend for security + runtime state."""
        if self == DeploymentProfile.CLOUD:
            return "external"
        return "filesystem"

    @property
    def conversation_backend(self) -> str:
        """Logical persistence backend for multi-turn memory."""
        if self == DeploymentProfile.CLOUD:
            return "external"
        return "memory"