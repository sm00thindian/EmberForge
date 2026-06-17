"""Structured setup status for the local /setup website."""

from __future__ import annotations

from emberforge import __version__
from emberforge.services.personas import load_personas
from emberforge.settings import Settings

_SENSITIVE_KEYS = frozenset(
    {
        "XAI_API_KEY",
        "GROK_API_KEY",
        "EMBER_LLM_API_KEY",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_DEFAULT_VOICE_ID",
        "EMBER_ADMIN_TOKEN",
        "EMBER_ADMIN_TOTP_SECRET",
        "EMBER_DEVICE_TOKEN",
    }
)

_CONFIG_KEYS = (
    "XAI_API_KEY",
    "GROK_API_KEY",
    "EMBER_LLM_MODEL",
    "EMBER_LLM_API_URL",
    "EMBER_LLM_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_DEFAULT_VOICE_ID",
    "ELEVENLABS_MODEL",
    "EMBER_ENV",
    "EMBER_CONTEXT_ENABLED",
    "EMBER_LAT",
    "EMBER_LON",
    "EMBER_LOCATION_NAME",
    "EMBER_TIMEZONE",
    "EMBER_CONTEXT_PROFILE_FILE",
    "EMBER_RSS_FEEDS",
    "EMBER_CONTEXT_MAX_HEADLINES",
    "EMBER_TOOLS_ENABLED",
    "EMBER_TOOLS_MAX_ROUNDS",
    "EMBER_PERSONA",
    "EMBER_WHISPER_MODEL",
    "EMBER_ADMIN_TOTP_SECRET",
    "EMBER_RATE_LIMIT_ENABLED",
    "EMBER_CONVERSATION_MAX_TURNS",
    "EMBER_HOST",
    "EMBER_BACKEND_PORT",
)


def mask_secret(value: str) -> str:
    """Return a masked representation safe for API responses."""
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"


def read_env_values(path) -> dict[str, str]:
    """Parse key/value pairs from a .env file."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        value = raw.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def build_config_snapshot(settings: Settings, *, mask_secrets: bool = True) -> dict[str, str]:
    """Return setup-relevant env values, optionally masked."""
    env_path = settings.project_root / ".env"
    raw = read_env_values(env_path)
    snapshot: dict[str, str] = {}
    for key in _CONFIG_KEYS:
        value = raw.get(key, "")
        if not value:
            if key == "EMBER_LLM_MODEL":
                value = settings.llm_model
            elif key == "EMBER_ENV":
                value = settings.ember_env
            elif key == "EMBER_CONTEXT_ENABLED":
                value = "true" if settings.context_enabled else "false"
            elif key == "EMBER_TOOLS_ENABLED":
                value = "true" if settings.tools_enabled else "false"
        if mask_secrets and key in _SENSITIVE_KEYS:
            snapshot[key] = mask_secret(value) if value else ""
        else:
            snapshot[key] = value
    return snapshot


def build_setup_status(settings: Settings) -> dict:
    """Aggregate readiness information for the setup UI."""
    issues: list[str] = []
    warnings: list[str] = []

    if not settings.resolved_api_key:
        issues.append("XAI_API_KEY is not set")

    if settings.context_enabled and not settings.context_location_configured:
        warnings.append("Context is enabled but location is not configured")

    if settings.tools_enabled and not settings.rss_feed_urls:
        warnings.append("News tools are enabled but EMBER_RSS_FEEDS is empty")

    paired = 0
    if settings.is_production:
        from emberforge.security.runtime import get_security_state

        paired = len(get_security_state()["device_registry"].list_devices())
        if paired == 0 and not settings.device_token:
            issues.append("Production mode requires at least one paired device or EMBER_DEVICE_TOKEN")

    personas_ok = True
    persona_ids: list[str] = []
    try:
        personas = load_personas(settings)
        persona_ids = sorted(personas)
    except Exception as exc:
        personas_ok = False
        issues.append(f"Personas failed to load: {exc}")

    runtime_ok = True
    try:
        settings.validate_runtime()
    except Exception as exc:
        runtime_ok = False
        issues.append(str(exc))

    return {
        "ready": runtime_ok and personas_ok and not issues,
        "issues": issues,
        "warnings": warnings,
        "version": __version__,
        "ember_env": settings.ember_env,
        "setup_url": "/setup",
        "api_key_set": bool(settings.resolved_api_key),
        "context_enabled": settings.context_enabled,
        "context_location_configured": settings.context_location_configured,
        "location": {
            "name": settings.location_name,
            "lat": settings.ember_lat,
            "lon": settings.ember_lon,
            "timezone": settings.timezone,
        },
        "rss_feed_count": len(settings.rss_feed_urls),
        "tools_enabled": settings.tools_enabled,
        "server_tts_available": settings.server_tts_available,
        "admin_auth_configured": settings.admin_auth_configured,
        "totp_configured": bool(settings.admin_totp_secret),
        "device_auth_required": settings.device_auth_required,
        "paired_device_count": paired,
        "personas": persona_ids,
        "default_persona": settings.default_persona_id,
    }