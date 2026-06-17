"""LLM configuration helpers — OpenAI-compatible chat completions."""

from __future__ import annotations

from emberforge.services.personas import Persona
from emberforge.settings import Settings

DEFAULT_LLM_MODEL = "grok-3-latest"
DEFAULT_LLM_API_URL = "https://api.x.ai/v1/chat/completions"


def resolve_llm_model(
    *,
    settings: Settings,
    persona: Persona | None = None,
    model: str | None = None,
) -> str:
    """
    Pick the model for a conversation turn.

    Priority: per-request override → persona default → global settings.
    """
    if model and model.strip():
        return model.strip()
    if persona and persona.model:
        return persona.model
    return settings.llm_model


def llm_models_probe_url(api_url: str) -> str:
    """Derive a /models probe URL from an OpenAI-compatible chat completions endpoint."""
    trimmed = api_url.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed[: -len("/chat/completions")] + "/models"
    return trimmed.rsplit("/", 1)[0] + "/models"