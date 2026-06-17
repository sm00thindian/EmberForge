"""Settings and configuration tests."""

from __future__ import annotations

import pytest

from emberforge.paths import get_project_root
from emberforge.settings import Settings, get_settings


def test_project_root_exists():
    root = get_project_root()
    assert (root / "personas").is_dir()
    assert (root / "pyproject.toml").is_file()


def test_resolved_api_key_prefers_xai(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "primary-key")
    monkeypatch.setenv("GROK_API_KEY", "legacy-key")
    monkeypatch.setenv("EMBERFORGE_ROOT", str(get_project_root()))
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.resolved_api_key == "primary-key"


def test_resolved_api_key_falls_back_to_grok(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("EMBER_LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "legacy-key")
    monkeypatch.setenv("EMBERFORGE_ROOT", str(get_project_root()))
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.resolved_api_key == "legacy-key"


def test_validate_runtime_requires_api_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("EMBER_LLM_API_KEY", raising=False)
    monkeypatch.setenv("EMBERFORGE_ROOT", str(get_project_root()))
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    with pytest.raises(RuntimeError, match="XAI_API_KEY"):
        settings.validate_runtime()


def test_validate_runtime_ok(test_settings: Settings):
    test_settings.validate_runtime()