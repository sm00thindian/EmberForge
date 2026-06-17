"""M3 contract tests — /device/v1/ response shapes."""

from __future__ import annotations

from tests.device_contract import assert_matches_schema


def test_device_capabilities_matches_schema(client):
    response = client.get("/device/v1/capabilities")
    assert response.status_code == 200
    assert_matches_schema(response.json(), "capabilities.response.json")


def test_device_personas_matches_schema(client):
    response = client.get("/device/v1/personas")
    assert response.status_code == 200
    assert_matches_schema(response.json(), "personas.response.json")


def test_device_converse_text_matches_schema(client_with_mock):
    response = client_with_mock.post(
        "/device/v1/converse/text",
        json={
            "message": "Open the pod bay doors",
            "persona": "hal_9000",
            "device_id": "contract-test-001",
        },
    )
    assert response.status_code == 200
    assert_matches_schema(response.json(), "converse.response.json")


def test_device_converse_audio_matches_schema(client_with_mock):
    response = client_with_mock.post(
        "/device/v1/converse",
        files={"audio": ("sample.wav", b"RIFFfake", "audio/wav")},
        data={"persona": "ember", "device_id": "contract-test-audio"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == "contract-test-audio"
    assert_matches_schema(body, "converse.response.json")


def test_device_error_response_matches_schema(client_with_mock):
    response = client_with_mock.post(
        "/device/v1/converse/text",
        json={"message": "Hello", "persona": "not_a_real_persona"},
    )
    assert response.status_code == 404
    assert_matches_schema(response.json(), "error.response.json")