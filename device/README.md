# Consumer Device Integration

EmberForge is designed so **consumer-grade hardware stays simple** while the backend carries the intelligence.

## Architecture

```
┌─────────────────────────┐         WiFi          ┌──────────────────────────┐
│  Consumer Device        │ ◄──────────────────► │  EmberForge Backend       │
│  (ESP32-S3, etc.)       │                       │  (local, Docker, or AWS) │
│                         │                       │                          │
│  • Push-to-talk button  │   POST /device/v1/    │  • Persona engine        │
│  • Microphone           │        converse       │  • Grok / xAI LLM        │
│  • Speaker              │                       │  • Whisper STT           │
│  • Small display        │   GET  /device/v1/    │  • TTS (planned)         │
│  • WiFi only            │        personas       │  • Custom voice clones   │
└─────────────────────────┘                       └──────────────────────────┘
```

**The device never needs API keys, persona prompts, or LLM logic.** It records audio, uploads it, and plays/displays the response.

## Device API (stable contract)

All device endpoints live under `/device/v1/`. This version will remain backward-compatible as features are added.

| Endpoint | Purpose |
|----------|---------|
| `GET /device/v1/capabilities` | Check server features on boot (includes `hub` deployment metadata) |
| `GET /device/v1/personas` | List personas for a device menu |
| `POST /device/v1/converse` | Upload WAV audio → transcript + reply |
| `POST /device/v1/converse/text` | Send pre-transcribed text |

### Boot sequence (recommended)

1. Connect to WiFi
2. `GET /device/v1/capabilities` — confirm server is reachable and STT is available
3. `GET /device/v1/personas` — populate persona selector
4. On button **hold** (push-to-talk): record WAV → `POST /device/v1/converse` → play/display result

Recommended device recording limits: **12s hard cap**, **1.5s trailing silence** fallback, **0.4s** minimum speech. The Mac dev client uses the same semantics with a **30s** cap (`emberforge/client/recording.py`).

### Audio format

| Field | Value |
|-------|-------|
| Format | WAV |
| Encoding | 16-bit PCM (`pcm_s16le`) |
| Channels | Mono |
| Sample rate | 16 kHz preferred |

### Response shape

Every converse response returns the same JSON structure:

```json
{
  "request_id": "uuid",
  "transcript": "what the user said",
  "response_text": "persona reply",
  "persona": { "id": "ember", "name": "Ember" },
  "voice": {
    "provider": "macos_say",
    "format": null,
    "audio_url": null,
    "audio_base64": null
  },
  "display": {
    "title": "Ember",
    "lines": ["Short lines for", "small OLED screens"]
  },
  "timestamp": "2026-06-16T..."
}
```

When server-side TTS is enabled, `voice.audio_base64` or `voice.audio_url` will carry playable audio so the device can speak without local TTS.

### JSON Schema (contract)

Response shapes are defined in [`schemas/v1/`](schemas/v1/) and validated in CI (`tests/test_device_contract.py`).

## Device auth

In **development** (default), the device API is open unless you set `EMBER_DEVICE_TOKEN`.

In **production** (`EMBER_ENV=production`), every `/device/v1/*` request (except pairing) requires a bearer token.

### Option A — shared token (simple)

Set `EMBER_DEVICE_TOKEN` on the backend (min 16 characters). Devices send:

```
Authorization: Bearer <token>
```

### Option B — per-device pairing (recommended)

1. On the backend host: `emberforge pair` or open **http://127.0.0.1:8000/setup** → Security & Devices (issues a 6-character code, localhost-only in production)
2. Device calls `POST /device/v1/pair/confirm`:

```json
{ "code": "ABC123", "device_id": "esp32-living-room", "name": "Living Room" }
```

3. Response includes `device_token` — **store it on the device; it is shown once.**

See [`docs/M7_SECURITY.md`](../docs/M7_SECURITY.md) for TOTP admin sessions and rate limits.

## Firmware scaffold

See `firmware/esp32-voice-client/` for a starter ESP32-S3 sketch that follows this contract.

## Deployment targets for the backend

The same `/device/v1/` contract works regardless of where the hub runs:

| Target | Typical URL | `EMBER_DEPLOYMENT` |
|--------|-------------|---------------------|
| Mac venv (development) | `http://127.0.0.1:8000` | `local` (default) |
| Docker home hub | `http://<lan-ip>:8000` | `docker` |
| Hosted AWS (future) | `https://api.<domain>` | `cloud` |

Consumer devices store the hub base URL and `device_token` in NVS at provisioning time. Firmware does not need to change when moving from a LAN hub to a hosted one — only the URL and pairing flow differ.

Architecture and commercial path: [`docs/HUB_ARCHITECTURE.md`](../docs/HUB_ARCHITECTURE.md), [`docs/ROADMAP.md`](../docs/ROADMAP.md).