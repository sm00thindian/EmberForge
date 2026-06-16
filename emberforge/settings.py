"""Central configuration for the EmberForge backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from emberforge.paths import get_project_root


class Settings(BaseSettings):
    """All backend configuration loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    xai_api_key: str = Field(default="", validation_alias="XAI_API_KEY")
    grok_api_key: str = Field(default="", validation_alias="GROK_API_KEY")

    # xAI / Grok
    xai_api_url: str = "https://api.x.ai/v1/chat/completions"
    xai_model: str = "grok-3-latest"
    xai_timeout_seconds: float = 60.0
    xai_max_tokens: int = 1200
    xai_max_retries: int = Field(default=3, validation_alias="XAI_MAX_RETRIES")
    xai_retry_base_seconds: float = Field(default=0.5, validation_alias="XAI_RETRY_BASE_SECONDS")

    # Server
    host: str = Field(default="127.0.0.1", validation_alias="EMBER_HOST")
    port: int = Field(default=8000, validation_alias="EMBER_BACKEND_PORT")
    log_level: str = "INFO"

    # Speech-to-text (server-side, for device uploads)
    whisper_model: str = Field(default="base", validation_alias="EMBER_WHISPER_MODEL")

    # Text-to-speech (server-side, for device playback)
    elevenlabs_api_key: str = Field(default="", validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_api_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_model: str = Field(default="eleven_turbo_v2_5", validation_alias="ELEVENLABS_MODEL")
    elevenlabs_default_voice_id: str = Field(default="", validation_alias="ELEVENLABS_DEFAULT_VOICE_ID")
    elevenlabs_timeout_seconds: float = 60.0
    elevenlabs_max_retries: int = Field(default=2, validation_alias="ELEVENLABS_MAX_RETRIES")
    elevenlabs_retry_base_seconds: float = Field(
        default=0.5,
        validation_alias="ELEVENLABS_RETRY_BASE_SECONDS",
    )
    device_tts_fallback: bool = Field(default=True, validation_alias="EMBER_DEVICE_TTS_FALLBACK")

    # Mac client TTS: macos_say (default), elevenlabs, or auto (ElevenLabs when configured)
    mac_tts_mode: str = Field(default="macos_say", validation_alias="EMBER_MAC_TTS")

    # Device API
    device_token: str = Field(default="", validation_alias="EMBER_DEVICE_TOKEN")
    max_audio_bytes: int = Field(default=1_048_576, validation_alias="EMBER_MAX_AUDIO_BYTES")
    device_api_version: str = "1"

    # Health checks
    health_disk_min_bytes: int = Field(
        default=100_000_000,
        validation_alias="EMBER_HEALTH_DISK_MIN_BYTES",
    )

    # Personas
    default_persona_id: str = "ember"

    # Optional explicit project root override
    emberforge_root: str = Field(default="", validation_alias="EMBERFORGE_ROOT")

    @property
    def resolved_api_key(self) -> str:
        return self.xai_api_key or self.grok_api_key

    @property
    def project_root(self) -> Path:
        if self.emberforge_root:
            return Path(self.emberforge_root).resolve()
        return get_project_root()

    @property
    def personas_dir(self) -> Path:
        return self.project_root / "personas"

    @property
    def device_auth_required(self) -> bool:
        return bool(self.device_token)

    @property
    def server_tts_available(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @field_validator("mac_tts_mode")
    @classmethod
    def validate_mac_tts_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"macos_say", "elevenlabs", "auto"}
        if normalized not in allowed:
            raise ValueError(f"mac_tts_mode must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @property
    def mac_elevenlabs_ready(self) -> bool:
        return self.server_tts_available and bool(self.elevenlabs_default_voice_id)

    @field_validator("max_audio_bytes")
    @classmethod
    def validate_max_audio_bytes(cls, value: int) -> int:
        if value < 1024:
            raise ValueError("max_audio_bytes must be at least 1024")
        return value

    def validate_runtime(self) -> None:
        """Fail fast when required secrets or paths are missing."""
        if not self.resolved_api_key:
            raise RuntimeError(
                "XAI_API_KEY is not set. Export it in your shell or add it to .env"
            )
        if not self.personas_dir.is_dir():
            raise RuntimeError(f"Personas directory not found: {self.personas_dir}")


@lru_cache
def get_settings() -> Settings:
    return Settings()