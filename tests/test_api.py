"""HTTP API integration tests."""

from __future__ import annotations

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "emberforge"
    assert body["device_api_version"] == "1"


def test_list_personas(client):
    response = client.get("/personas")
    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "ember"
    ids = {item["id"] for item in body["personas"]}
    assert ids == {"ember", "hal_9000"}


def test_chat(client_with_mock):
    response = client_with_mock.post(
        "/chat",
        json={"message": "Hello", "persona": "ember"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["persona"] == "ember"
    assert "Reply from Ember" in body["response"]


def test_chat_unknown_persona(client_with_mock):
    response = client_with_mock.post(
        "/chat",
        json={"message": "Hello", "persona": "missing"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "PERSONA_NOT_FOUND"
    assert body["retryable"] is False


def test_device_capabilities(client):
    response = client.get("/device/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "1"
    assert body["features"]["personas"] is True


def test_device_personas(client):
    response = client.get("/device/v1/personas")
    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "ember"
    assert len(body["personas"]) >= 2


def test_device_converse_text(client_with_mock):
    response = client_with_mock.post(
        "/device/v1/converse/text",
        json={
            "message": "Hello device",
            "persona": "hal_9000",
            "device_id": "test-device-001",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "Hello device"
    assert body["persona"]["id"] == "hal_9000"
    assert body["display"]["title"] == "HAL"
    assert "request_id" in body