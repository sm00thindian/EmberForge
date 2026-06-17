"""LLM configuration tests."""

from __future__ import annotations

from emberforge.services.llm import llm_models_probe_url, resolve_llm_model
from emberforge.services.personas import Persona, VoiceConfig
from emberforge.settings import Settings


def _persona(**overrides) -> Persona:
    base = dict(
        id="ember",
        name="Ember",
        tagline="",
        system_prompt="You are Ember.",
        voice=VoiceConfig(provider="macos_say", voice="Shelley (English (US))"),
        temperature=0.7,
        type="companion",
        model=None,
    )
    base.update(overrides)
    return Persona(**base)


def test_resolve_llm_model_defaults_to_settings(test_settings: Settings):
    assert resolve_llm_model(settings=test_settings, persona=_persona()) == "grok-3-latest"


def test_resolve_llm_model_prefers_persona_override(test_settings: Settings):
    persona = _persona(model="grok-3-mini")
    assert resolve_llm_model(settings=test_settings, persona=persona) == "grok-3-mini"


def test_resolve_llm_model_prefers_request_override(test_settings: Settings):
    persona = _persona(model="grok-3-mini")
    assert (
        resolve_llm_model(settings=test_settings, persona=persona, model="gpt-4o")
        == "gpt-4o"
    )


def test_llm_models_probe_url_from_chat_completions():
    url = "https://api.x.ai/v1/chat/completions"
    assert llm_models_probe_url(url) == "https://api.x.ai/v1/models"


def test_settings_llm_env_aliases(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.setenv("EMBER_LLM_MODEL", "grok-2-latest")
    monkeypatch.setenv("EMBER_LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    monkeypatch.setenv("EMBER_LLM_API_KEY", "openai-key")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    settings = Settings()
    assert settings.llm_model == "grok-2-latest"
    assert settings.llm_api_url == "https://api.openai.com/v1/chat/completions"
    assert settings.resolved_llm_api_key == "openai-key"
    get_settings.cache_clear()