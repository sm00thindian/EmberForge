"""Hub runtime and deployment profile tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from emberforge.api.app import create_app
from emberforge.hub import (
    DeploymentProfile,
    build_hub,
    scoped_session_id,
)
from emberforge.settings import Settings, get_settings


def test_deployment_profile_maker_defaults():
    profile = DeploymentProfile.LOCAL
    assert profile.is_maker_hosted
    assert profile.allows_env_file_writes
    assert profile.state_backend == "filesystem"
    assert profile.conversation_backend == "memory"


def test_deployment_profile_cloud_flags():
    profile = DeploymentProfile.CLOUD
    assert not profile.is_maker_hosted
    assert not profile.allows_env_file_writes
    assert profile.state_backend == "external"
    assert profile.conversation_backend == "external"


def test_scoped_session_id_preserves_maker_behavior():
    assert scoped_session_id("", "device-42") == "device-42"
    assert scoped_session_id("  ", "device-42") == "device-42"


def test_scoped_session_id_namespaces_tenant():
    assert scoped_session_id("acct-1", "device-42") == "acct-1:device-42"


def test_build_hub_loads_personas(test_settings: Settings):
    hub = build_hub(test_settings)
    assert hub.deployment == DeploymentProfile.LOCAL
    assert "ember" in hub.personas
    assert hub.layout.personas_dir == test_settings.project_root / "personas"
    assert hub.stores.config.allows_writes is True
    assert hub.converse.history is hub.stores.conversation
    caps = hub.as_capabilities()
    assert caps["deployment"] == "local"
    assert caps["tenant_mode"] == "single"


def test_hub_config_store_upsert_and_read(test_settings: Settings, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("XAI_API_KEY=old\n", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        emberforge_root=str(tmp_path),
        xai_api_key="old",
    )
    hub = build_hub(settings)
    hub.stores.config.upsert({"XAI_API_KEY": "new-key"})
    assert hub.stores.config.read_values()["XAI_API_KEY"] == "new-key"


def test_cloud_config_store_blocks_writes(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_DEPLOYMENT", "cloud")
    get_settings.cache_clear()
    settings = Settings(
        _env_file=None,
        emberforge_root=str(test_settings.project_root),
        xai_api_key="test-key",
    )
    hub = build_hub(settings)
    assert hub.deployment == DeploymentProfile.CLOUD
    assert hub.stores.config.allows_writes is False
    with pytest.raises(RuntimeError, match="disabled"):
        hub.stores.config.upsert({"XAI_API_KEY": "nope"})
    get_settings.cache_clear()


def test_settings_rejects_unknown_deployment(monkeypatch):
    monkeypatch.setenv("EMBER_DEPLOYMENT", "edge")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="ember_deployment"):
        Settings()


def test_device_capabilities_exposes_hub(client):
    response = client.get("/device/v1/capabilities")
    assert response.status_code == 200
    hub = response.json()["hub"]
    assert hub["deployment"] == "local"
    assert hub["setup_env_file_writes"] is True


def test_cloud_deployment_blocks_setup_config_writes(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_DEPLOYMENT", "cloud")
    get_settings.cache_clear()
    settings = Settings(
        _env_file=None,
        emberforge_root=str(test_settings.project_root),
        xai_api_key="test-key",
    )
    app = create_app(settings)
    client = TestClient(app)
    response = client.patch("/setup/v1/config", json={"values": {"XAI_API_KEY": "new"}})
    assert response.status_code == 501
    get_settings.cache_clear()