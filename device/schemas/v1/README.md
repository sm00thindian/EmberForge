# Device API v1 — JSON Schemas

Canonical response shapes for `/device/v1/`. Firmware and integrators should treat these as the stable contract.

| Schema | Endpoint |
|--------|----------|
| `capabilities.response.json` | `GET /device/v1/capabilities` |
| `personas.response.json` | `GET /device/v1/personas` |
| `converse.response.json` | `POST /device/v1/converse/text`, `POST /device/v1/converse` |
| `error.response.json` | Error responses (`4xx` / `5xx`) |

Contract tests: `tests/test_device_contract.py`