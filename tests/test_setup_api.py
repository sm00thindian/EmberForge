"""Local setup website API and static UI."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from emberforge.api.app import create_app
from emberforge.paths import get_project_root
from emberforge.security.runtime import reset_security_state
from emberforge.settings import Settings, get_settings

REMOTE = {"X-Forwarded-For": "203.0.113.1"}


@pytest.fixture
def isolated_root(tmp_path):
    root = tmp_path / "forge"
    project = get_project_root()
    shutil.copytree(project / "personas", root / "personas")
    shutil.copytree(project / "prompts", root / "prompts")
    shutil.copytree(project / "emberforge" / "web", root / "emberforge" / "web")
    env = root / ".env"
    env.write_text("XAI_API_KEY=test-key\nEMBER_ENV=development\n", encoding="utf-8")
    return root


@pytest.fixture
def setup_client(isolated_root, monkeypatch):
    monkeypatch.setenv("EMBERFORGE_ROOT", str(isolated_root))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_ENV", "development")
    get_settings.cache_clear()
    reset_security_state()
    client = TestClient(create_app(Settings()))
    yield client, isolated_root
    get_settings.cache_clear()
    reset_security_state()


def test_setup_status(setup_client):
    client, _ = setup_client
    response = client.get("/setup/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_key_set"] is True
    assert "ember" in data["personas"]
    assert data["setup_url"] == "/setup"


def test_setup_config_mask_and_patch(setup_client):
    client, root = setup_client
    get = client.get("/setup/v1/config")
    assert get.status_code == 200
    values = get.json()["values"]
    assert values["XAI_API_KEY"].startswith("••••")

    patch = client.patch(
        "/setup/v1/config",
        json={"values": {"EMBER_CONTEXT_ENABLED": "true", "EMBER_RSS_FEEDS": "https://example.test/feed.xml"}},
    )
    assert patch.status_code == 200
    assert "EMBER_CONTEXT_ENABLED" in patch.json()["updated"]

    env_text = (root / ".env").read_text(encoding="utf-8")
    assert "EMBER_CONTEXT_ENABLED=true" in env_text
    assert "https://example.test/feed.xml" in env_text


def test_setup_profile_roundtrip(setup_client):
    client, root = setup_client
    profile_path = root / "prompts" / "user_context.md"

    put = client.put("/setup/v1/profile", json={"content": "# Test profile\n- motorcycles"})
    assert put.status_code == 200

    get = client.get("/setup/v1/profile")
    assert get.status_code == 200
    assert "motorcycles" in get.json()["content"]
    assert profile_path.read_text(encoding="utf-8").startswith("# Test profile")


def test_setup_static_ui(setup_client):
    client, _ = setup_client
    index = client.get("/setup")
    assert index.status_code == 200
    assert "EmberForge Setup" in index.text

    css = client.get("/setup/styles.css")
    assert css.status_code == 200
    assert "ember" in css.text

    js = client.get("/setup/app.js")
    assert js.status_code == 200
    assert "setup/v1/status" in js.text

    icon = client.get("/setup/favicon.svg")
    assert icon.status_code == 200
    assert "image/svg+xml" in icon.headers.get("content-type", "")
    assert "e86a2a" in icon.text

    root_icon = client.get("/favicon.ico")
    assert root_icon.status_code == 200


def test_admin_devices_list_and_revoke(setup_client):
    client, _ = setup_client
    empty = client.get("/admin/v1/devices")
    assert empty.status_code == 200
    assert empty.json()["devices"] == []

    confirm = client.post(
        "/device/v1/pair/confirm",
        json={"code": client.post("/admin/v1/pair/code").json()["code"], "device_id": "test-unit", "name": "Test"},
    )
    assert confirm.status_code == 200

    listed = client.get("/admin/v1/devices")
    assert len(listed.json()["devices"]) == 1
    assert listed.json()["devices"][0]["device_id"] == "test-unit"

    revoked = client.delete("/admin/v1/devices/test-unit")
    assert revoked.status_code == 200
    assert client.get("/admin/v1/devices").json()["devices"] == []


def test_chat_voice_flags_pass_through(setup_client, monkeypatch):
    client, _ = setup_client

    async def fake_text(persona_id, message, **kwargs):
        from emberforge.services.conversation import ConversationResult

        assert kwargs.get("synthesize_audio") is True
        assert kwargs.get("play_audio") is True
        assert kwargs.get("session_id") == "web-test-session"
        return ConversationResult(
            request_id="req-voice",
            transcript=message,
            response_text="Hello with voice",
            persona_id=persona_id,
            persona_name="Ember",
            voice={
                "provider": "elevenlabs",
                "format": "mp3",
                "audio_base64": "aGVsbG8=",
                "played_locally": False,
            },
            display_lines=["Hello with voice"],
            timestamp="2026-06-16T12:00:00+00:00",
            model="grok-3-latest",
            session_id=kwargs.get("session_id"),
            history_turns=2,
        )

    converse = client.app.state.converse
    monkeypatch.setattr(converse, "converse_text", fake_text)

    response = client.post(
        "/chat",
        json={
            "message": "Hi",
            "persona": "ember",
            "session_id": "web-test-session",
            "synthesize_audio": True,
            "play_audio": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["voice"]["audio_base64"] == "aGVsbG8="
    assert data["response"] == "Hello with voice"
    assert data["session_id"] == "web-test-session"
    assert data["history_turns"] == 2


def test_setup_mutations_blocked_remotely_in_production(isolated_root, monkeypatch):
    monkeypatch.setenv("EMBERFORGE_ROOT", str(isolated_root))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_ENV", "production")
    get_settings.cache_clear()
    reset_security_state()

    client = TestClient(create_app(Settings()))
    response = client.patch(
        "/setup/v1/config",
        json={"values": {"EMBER_CONTEXT_ENABLED": "true"}},
        headers=REMOTE,
    )
    assert response.status_code == 403

    get_settings.cache_clear()
    reset_security_state()