"""M7 security: device auth, TOTP sessions, pairing, rate limits, redaction."""

from __future__ import annotations

import logging
import shutil

import pyotp
import pytest
from fastapi.testclient import TestClient

from emberforge.api.app import create_app
from emberforge.paths import get_project_root
from emberforge.security.rate_limit import get_rate_limiter
from emberforge.security.redaction import SecretRedactionFilter, redact_secrets
from emberforge.security.runtime import reset_security_state
from emberforge.settings import Settings, get_settings

TOTP_SECRET = "JBSWY3DPEHPK3PXP"
REMOTE = {"X-Forwarded-For": "203.0.113.1"}


@pytest.fixture
def isolated_root(tmp_path):
    """Minimal project tree with personas and prompts for isolated .emberforge state."""
    root = tmp_path / "forge"
    project = get_project_root()
    shutil.copytree(project / "personas", root / "personas")
    shutil.copytree(project / "prompts", root / "prompts")
    return root


@pytest.fixture
def prod_client(isolated_root, monkeypatch):
    monkeypatch.setenv("EMBERFORGE_ROOT", str(isolated_root))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_ENV", "production")
    monkeypatch.delenv("EMBER_DEVICE_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_security_state()
    get_rate_limiter().reset()

    settings = Settings()
    client = TestClient(create_app(settings))
    yield client, settings

    get_settings.cache_clear()
    reset_security_state()
    get_rate_limiter().reset()


def _current_totp() -> str:
    return pyotp.TOTP(TOTP_SECRET).now()


def test_redact_secrets_masks_bearer_and_env_keys():
    raw = "Authorization: Bearer super-secret-token XAI_API_KEY=abc123"
    redacted = redact_secrets(raw)
    assert "super-secret-token" not in redacted
    assert "abc123" not in redacted
    assert "[REDACTED]" in redacted


def test_secret_redaction_filter_on_log_record():
    filt = SecretRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="token EMBER_DEVICE_TOKEN=leaked-value",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "leaked-value" not in record.msg


def test_production_requires_device_token(prod_client):
    client, _ = prod_client
    response = client.get("/device/v1/capabilities")
    assert response.status_code == 401


def test_legacy_device_token_accepted(isolated_root, monkeypatch):
    token = "a" * 16
    monkeypatch.setenv("EMBERFORGE_ROOT", str(isolated_root))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_ENV", "production")
    monkeypatch.setenv("EMBER_DEVICE_TOKEN", token)
    get_settings.cache_clear()
    reset_security_state()

    client = TestClient(create_app(Settings()))
    response = client.get("/device/v1/capabilities", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    get_settings.cache_clear()
    reset_security_state()


def test_pairing_flow_issues_token(prod_client):
    client, _ = prod_client

    code_response = client.post("/admin/v1/pair/code")
    assert code_response.status_code == 200
    code = code_response.json()["code"]

    confirm = client.post(
        "/device/v1/pair/confirm",
        json={"code": code, "device_id": "esp32-test", "name": "Lab Unit"},
    )
    assert confirm.status_code == 200
    device_token = confirm.json()["device_token"]

    authed = client.get(
        "/device/v1/capabilities",
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert authed.status_code == 200


def test_pairing_code_localhost_only_in_production(prod_client):
    client, _ = prod_client
    response = client.post("/admin/v1/pair/code", headers=REMOTE)
    assert response.status_code == 403


def test_admin_localhost_trusted_without_credentials(prod_client):
    client, _ = prod_client
    response = client.get("/personas")
    assert response.status_code == 200


def test_admin_remote_requires_auth(prod_client, monkeypatch):
    client, settings = prod_client
    monkeypatch.setenv("EMBER_ADMIN_TOTP_SECRET", TOTP_SECRET)
    get_settings.cache_clear()
    reset_security_state()

    client = TestClient(create_app(Settings()))
    response = client.get("/personas", headers=REMOTE)
    assert response.status_code == 401


def test_totp_session_grants_remote_admin_access(prod_client, monkeypatch):
    monkeypatch.setenv("EMBER_ADMIN_TOTP_SECRET", TOTP_SECRET)
    get_settings.cache_clear()
    reset_security_state()

    client = TestClient(create_app(Settings()))

    session = client.post("/admin/v1/session", json={"totp": _current_totp()})
    assert session.status_code == 200
    access_token = session.json()["access_token"]

    authed = client.get(
        "/personas",
        headers={**REMOTE, "Authorization": f"Bearer {access_token}"},
    )
    assert authed.status_code == 200


def test_totp_setup_returns_provisioning_uri(prod_client, monkeypatch):
    monkeypatch.setenv("EMBER_ADMIN_TOTP_SECRET", TOTP_SECRET)
    get_settings.cache_clear()
    reset_security_state()

    client = TestClient(create_app(Settings()))
    response = client.get("/admin/v1/totp/setup")
    assert response.status_code == 200
    body = response.json()
    assert "otpauth://" in body["provisioning_uri"]


def test_rate_limit_returns_429(test_settings, monkeypatch):
    monkeypatch.setenv("EMBER_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("EMBER_RATE_LIMIT_DEFAULT_PER_MINUTE", "2")
    get_settings.cache_clear()
    reset_security_state()
    get_rate_limiter().reset()

    client = TestClient(create_app(Settings()))
    for _ in range(2):
        assert client.get("/personas").status_code == 200
    limited = client.get("/personas")
    assert limited.status_code == 429
    assert limited.json()["code"] == "RATE_LIMITED"

    get_settings.cache_clear()
    reset_security_state()
    get_rate_limiter().reset()


def test_validate_runtime_production_requires_device_auth(isolated_root, monkeypatch):
    monkeypatch.setenv("EMBERFORGE_ROOT", str(isolated_root))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_ENV", "production")
    monkeypatch.delenv("EMBER_DEVICE_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_security_state()

    settings = Settings()
    with pytest.raises(RuntimeError, match="EMBER_DEVICE_TOKEN"):
        settings.validate_runtime()

    get_settings.cache_clear()
    reset_security_state()