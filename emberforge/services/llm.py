"""LLM configuration helpers — OpenAI-compatible chat completions."""

from __future__ import annotations

from dataclasses import dataclass

from emberforge.services.personas import Persona
from emberforge.settings import Settings

GROK_PROVIDER = "grok"
CLAUDE_PROVIDER = "claude"

GROK_DEFAULT_MODEL = "grok-3-latest"
GROK_DEFAULT_API_URL = "https://api.x.ai/v1/chat/completions"

CLAUDE_DEFAULT_MODEL = "claude-sonnet-4-6"
CLAUDE_DEFAULT_API_URL = "https://api.anthropic.com/v1/chat/completions"

_SUPPORTED_PROVIDERS = frozenset({GROK_PROVIDER, CLAUDE_PROVIDER})


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model: str
    api_url: str
    api_key: str


def normalize_llm_provider(value: str) -> str:
    provider = value.strip().lower()
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"llm_provider must be one of: {', '.join(sorted(_SUPPORTED_PROVIDERS))}")
    return provider


def resolve_llm_model(
    *,
    settings: Settings,
    persona: Persona | None = None,
    model: str | None = None,
) -> str:
    """
    Pick the model for a conversation turn.

    Priority: per-request override → persona default → provider/global settings.
    """
    if model and model.strip():
        return model.strip()
    if persona and persona.model:
        return persona.model
    return settings.llm_model


def resolve_llm_config(
    *,
    settings: Settings,
    persona: Persona | None = None,
    model: str | None = None,
) -> LlmConfig:
    """Resolve provider, model, URL, and API key for an LLM request."""
    provider = normalize_llm_provider(settings.llm_provider)
    resolved_model = resolve_llm_model(settings=settings, persona=persona, model=model)

    if provider == CLAUDE_PROVIDER:
        api_key = settings.llm_api_key or settings.anthropic_api_key
        api_url = settings.llm_api_url
        if api_url == GROK_DEFAULT_API_URL:
            api_url = CLAUDE_DEFAULT_API_URL
        if resolved_model == GROK_DEFAULT_MODEL or resolved_model.startswith("grok"):
            resolved_model = CLAUDE_DEFAULT_MODEL
    else:
        api_key = settings.llm_api_key or settings.resolved_api_key
        api_url = settings.llm_api_url or GROK_DEFAULT_API_URL

    return LlmConfig(
        provider=provider,
        model=resolved_model,
        api_url=api_url,
        api_key=api_key,
    )


def llm_models_probe_url(api_url: str) -> str:
    """Derive a /models probe URL from an OpenAI-compatible chat completions endpoint."""
    trimmed = api_url.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed[: -len("/chat/completions")] + "/models"
    return trimmed.rsplit("/", 1)[0] + "/models"