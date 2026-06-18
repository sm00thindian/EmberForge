"""Central configuration for the EmberForge backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
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
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # LLM (OpenAI-compatible chat completions — defaults to xAI / Grok)
    llm_provider: str = Field(
        default="grok",
        validation_alias=AliasChoices("EMBER_LLM_PROVIDER", "EMBER_LLM_BACKEND"),
    )
    llm_model: str = Field(
        default="grok-3-latest",
        validation_alias=AliasChoices("EMBER_LLM_MODEL", "XAI_MODEL", "GROK_MODEL"),
    )
    llm_api_url: str = Field(
        default="https://api.x.ai/v1/chat/completions",
        validation_alias=AliasChoices("EMBER_LLM_API_URL", "XAI_API_URL"),
    )
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("EMBER_LLM_API_KEY"))
    xai_timeout_seconds: float = 60.0
    xai_max_tokens: int = 1200
    xai_max_retries: int = Field(default=3, validation_alias="XAI_MAX_RETRIES")
    xai_retry_base_seconds: float = Field(default=0.5, validation_alias="XAI_RETRY_BASE_SECONDS")

    # Server
    host: str = Field(default="0.0.0.0", validation_alias="EMBER_HOST")
    port: int = Field(default=8000, validation_alias="EMBER_BACKEND_PORT")
    log_level: str = "INFO"
    log_json: bool = Field(default=False, validation_alias="EMBER_LOG_JSON")

    # Speech-to-text (server-side, for device uploads)
    whisper_model: str = Field(default="base", validation_alias="EMBER_WHISPER_MODEL")

    # Text-to-speech (server-side, for device playback)
    elevenlabs_api_key: str = Field(default="", validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_api_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_model: str = Field(default="eleven_turbo_v2_5", validation_alias="ELEVENLABS_MODEL")
    elevenlabs_speed: float = Field(default=0.9, validation_alias="ELEVENLABS_SPEED")
    elevenlabs_sentence_pause_seconds: float = Field(
        default=0.4,
        validation_alias="ELEVENLABS_SENTENCE_PAUSE_SECONDS",
    )
    elevenlabs_default_voice_id: str = Field(default="", validation_alias="ELEVENLABS_DEFAULT_VOICE_ID")
    tts_pronunciations_file: str = Field(
        default="prompts/tts_pronunciations.json",
        validation_alias="EMBER_TTS_PRONUNCIATIONS_FILE",
    )
    elevenlabs_timeout_seconds: float = 60.0
    elevenlabs_max_retries: int = Field(default=2, validation_alias="ELEVENLABS_MAX_RETRIES")
    elevenlabs_retry_base_seconds: float = Field(
        default=0.5,
        validation_alias="ELEVENLABS_RETRY_BASE_SECONDS",
    )
    device_tts_fallback: bool = Field(default=True, validation_alias="EMBER_DEVICE_TTS_FALLBACK")

    # Mac client TTS per session (start_ember.sh exports EMBER_MAC_TTS; not stored in .env)
    mac_tts_mode: str = Field(default="macos_say", validation_alias="EMBER_MAC_TTS")

    # Environment / security (M7)
    ember_env: str = Field(
        default="development",
        validation_alias=AliasChoices("EMBER_ENV", "EMBER_ENVIRONMENT"),
    )
    admin_token: str = Field(default="", validation_alias="EMBER_ADMIN_TOKEN")
    admin_totp_secret: str = Field(default="", validation_alias="EMBER_ADMIN_TOTP_SECRET")
    rate_limit_enabled: bool = Field(default=False, validation_alias="EMBER_RATE_LIMIT_ENABLED")
    rate_limit_converse_per_minute: int = Field(
        default=20,
        validation_alias="EMBER_RATE_LIMIT_CONVERSE_PER_MINUTE",
    )
    rate_limit_default_per_minute: int = Field(
        default=120,
        validation_alias="EMBER_RATE_LIMIT_DEFAULT_PER_MINUTE",
    )
    pairing_code_ttl_seconds: float = Field(default=300.0, validation_alias="EMBER_PAIRING_CODE_TTL_SECONDS")
    admin_session_ttl_seconds: float = Field(
        default=28_800.0,
        validation_alias="EMBER_ADMIN_SESSION_TTL_SECONDS",
    )
    device_token_min_length: int = Field(default=16, validation_alias="EMBER_DEVICE_TOKEN_MIN_LENGTH")

    # Device API
    device_token: str = Field(default="", validation_alias="EMBER_DEVICE_TOKEN")
    max_audio_bytes: int = Field(default=1_048_576, validation_alias="EMBER_MAX_AUDIO_BYTES")
    device_api_version: str = "1"

    # Health checks
    health_disk_min_bytes: int = Field(
        default=100_000_000,
        validation_alias="EMBER_HEALTH_DISK_MIN_BYTES",
    )

    # Conversation memory
    conversation_max_turns: int = Field(
        default=20,
        validation_alias="EMBER_CONVERSATION_MAX_TURNS",
    )
    conversation_session_ttl_seconds: float = Field(
        default=86_400.0,
        validation_alias="EMBER_CONVERSATION_SESSION_TTL_SECONDS",
    )

    # Live context (weather, headlines, user profile)
    context_enabled: bool = Field(default=False, validation_alias="EMBER_CONTEXT_ENABLED")
    ember_lat: float | None = Field(default=None, validation_alias="EMBER_LAT")
    ember_lon: float | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBER_LON", "EMBER_LONG"),
    )
    location_name: str = Field(default="", validation_alias="EMBER_LOCATION_NAME")
    timezone: str = Field(default="", validation_alias="EMBER_TIMEZONE")
    context_profile_file: str = Field(
        default="prompts/user_context.md",
        validation_alias="EMBER_CONTEXT_PROFILE_FILE",
    )
    rss_feeds: str = Field(default="", validation_alias="EMBER_RSS_FEEDS")
    context_max_headlines: int = Field(default=5, validation_alias="EMBER_CONTEXT_MAX_HEADLINES")
    context_weather_cache_ttl_seconds: float = Field(
        default=1800.0,
        validation_alias="EMBER_CONTEXT_WEATHER_CACHE_TTL_SECONDS",
    )
    context_rss_cache_ttl_seconds: float = Field(
        default=14_400.0,
        validation_alias="EMBER_CONTEXT_RSS_CACHE_TTL_SECONDS",
    )
    context_fetch_timeout_seconds: float = Field(
        default=8.0,
        validation_alias="EMBER_CONTEXT_FETCH_TIMEOUT_SECONDS",
    )
    tools_enabled: bool = Field(default=True, validation_alias="EMBER_TOOLS_ENABLED")
    tools_max_rounds: int = Field(default=3, validation_alias="EMBER_TOOLS_MAX_ROUNDS")

    # Personas
    default_persona_id: str = "ember"

    # Optional explicit project root override
    emberforge_root: str = Field(default="", validation_alias="EMBERFORGE_ROOT")

    @property
    def resolved_api_key(self) -> str:
        return self.xai_api_key or self.grok_api_key

    @property
    def resolved_llm_api_key(self) -> str:
        from emberforge.services.llm import CLAUDE_PROVIDER, normalize_llm_provider

        provider = normalize_llm_provider(self.llm_provider)
        if provider == CLAUDE_PROVIDER:
            return self.llm_api_key or self.anthropic_api_key
        return self.llm_api_key or self.resolved_api_key

    @property
    def xai_model(self) -> str:
        """Backward-compatible alias for :attr:`llm_model`."""
        return self.llm_model

    @property
    def xai_api_url(self) -> str:
        """Backward-compatible alias for :attr:`llm_api_url`."""
        return self.llm_api_url

    @property
    def project_root(self) -> Path:
        if self.emberforge_root:
            return Path(self.emberforge_root).resolve()
        return get_project_root()

    @property
    def personas_dir(self) -> Path:
        return self.project_root / "personas"

    @property
    def context_location_configured(self) -> bool:
        return self.ember_lat is not None and self.ember_lon is not None

    @property
    def rss_feed_urls(self) -> list[str]:
        return [url.strip() for url in self.rss_feeds.split(",") if url.strip()]

    @property
    def is_production(self) -> bool:
        return self.ember_env.strip().lower() == "production"

    @property
    def security_state_dir(self) -> Path:
        return self.project_root / ".emberforge"

    @property
    def rate_limits_active(self) -> bool:
        return self.rate_limit_enabled or self.is_production

    @property
    def device_auth_required(self) -> bool:
        return self.is_production or bool(self.device_token)

    @property
    def admin_auth_configured(self) -> bool:
        return bool(self.admin_token or self.admin_totp_secret)

    @property
    def server_tts_available(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        from emberforge.services.llm import normalize_llm_provider

        return normalize_llm_provider(value)

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

    @field_validator("ember_env")
    @classmethod
    def validate_ember_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"development", "production"}
        if normalized not in allowed:
            raise ValueError(f"ember_env must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("elevenlabs_speed")
    @classmethod
    def validate_elevenlabs_speed(cls, value: float) -> float:
        if not 0.5 <= value <= 1.5:
            raise ValueError("elevenlabs_speed must be between 0.5 and 1.5")
        return value

    @field_validator("elevenlabs_sentence_pause_seconds")
    @classmethod
    def validate_elevenlabs_sentence_pause_seconds(cls, value: float) -> float:
        if not 0.0 <= value <= 1.5:
            raise ValueError("elevenlabs_sentence_pause_seconds must be between 0.0 and 1.5")
        return value

    @field_validator("max_audio_bytes")
    @classmethod
    def validate_max_audio_bytes(cls, value: int) -> int:
        if value < 1024:
            raise ValueError("max_audio_bytes must be at least 1024")
        return value

    def validate_runtime(self) -> None:
        """Fail fast when required secrets or paths are missing."""
        from emberforge.services.llm import CLAUDE_PROVIDER, normalize_llm_provider

        provider = normalize_llm_provider(self.llm_provider)
        if provider == CLAUDE_PROVIDER:
            if not self.resolved_llm_api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Required when EMBER_LLM_PROVIDER=claude"
                )
        elif not self.resolved_api_key:
            raise RuntimeError(
                "XAI_API_KEY is not set. Export it in your shell or add it to .env"
            )
        if not self.personas_dir.is_dir():
            raise RuntimeError(f"Personas directory not found: {self.personas_dir}")

        if self.is_production:
            from emberforge.security.runtime import get_security_state

            registry = get_security_state()["device_registry"]
            has_legacy_token = len(self.device_token) >= self.device_token_min_length
            if not has_legacy_token and not registry.has_devices():
                raise RuntimeError(
                    "Production requires EMBER_DEVICE_TOKEN "
                    f"(min {self.device_token_min_length} chars) or at least one paired device"
                )
            if self.host in {"0.0.0.0", "::"} and not self.admin_auth_configured:
                raise RuntimeError(
                    "Production on 0.0.0.0 requires EMBER_ADMIN_TOKEN or EMBER_ADMIN_TOTP_SECRET "
                    "for remote Mac API access"
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()