# Release 1.0 — EmberForge Backend

**Target:** A production-quality backend, fully developable and testable on Mac, with a stable API for consumer-grade devices.

Release 1.0 is the **server software only** — not the ESP32 firmware, not the web dashboard. It is the brain that Mac clients and physical devices talk to.

---

## What 1.0 Means

| Criteria | Definition |
|----------|------------|
| **Runnable on Mac** | `emberforge serve` starts the backend; `start_ember.sh` launches Mac voice mode |
| **Testable** | `pytest` passes; API and persona logic covered without live xAI calls |
| **Device-ready** | `/device/v1/` contract is stable, versioned, and documented |
| **Configurable** | All settings via environment / `.env`; fails fast with clear errors |
| **Packaged** | Installable Python package with pinned dependencies |
| **Documented** | This roadmap + API docs + device integration guide |

---

## Architecture (1.0)

```
emberforge/
├── settings.py          # Central configuration
├── paths.py             # Project root resolution
├── cli.py               # emberforge serve | check
├── services/
│   ├── personas.py      # Persona registry
│   ├── conversation.py  # Grok/xAI conversation engine
│   └── stt.py           # Server-side Whisper (device uploads)
└── api/
    ├── app.py           # FastAPI factory
    └── routes/
        ├── health.py    # /health, /version
        ├── chat.py      # /chat, /personas (Mac)
        └── device.py    # /device/v1/* (hardware)
```

**Principle:** Mac and devices share `services/conversation.py` and `ConverseService`. Clients differ in input path (local Whisper vs uploaded WAV) and output rendering (macOS `say`, optional ElevenLabs on Mac via `EMBER_MAC_TTS`, or server MP3 for devices).

---

## Milestone Checklist

### M1 — Project Foundation ✅ (this release starts here)

- [x] `emberforge` Python package
- [x] `pyproject.toml` with pinned dependencies
- [x] `emberforge serve` and `emberforge check` CLI
- [x] `python -m emberforge serve`
- [x] Backward-compatible `backend/main.py` shim

### M2 — Configuration ✅

- [x] `Settings` class (pydantic-settings)
- [x] `XAI_API_KEY` + legacy `GROK_API_KEY` support
- [x] `validate_runtime()` fail-fast on startup
- [x] `EMBERFORGE_ROOT` for non-standard install paths

### M3 — Tests & CI

- [x] pytest suite (settings, personas, conversation, API)
- [x] GitHub Actions CI workflow (`.github/workflows/test.yml`)
- [ ] Contract tests for `/device/v1/` response shape (JSON schema)

### M4 — Voice Pipeline Abstraction ✅

- [x] `STTProvider` / `TTSProvider` interfaces (`emberforge/services/voice/`)
- [x] `WhisperSTT` + `MacSayTTS` + `StubTTS` (placeholder for ElevenLabs)
- [x] Unified `ConverseService` (`emberforge/services/converse.py`)
- [x] Mac client uses same providers (`emberforge/client/mac_voice.py`)

### M5 — Server-Side TTS ✅

- [x] ElevenLabs `TTSProvider` (`emberforge/services/voice/elevenlabs_tts.py`)
- [x] `voice.audio_base64` (MP3) in device responses when `ELEVENLABS_API_KEY` is set
- [x] Voice profile loader links `voices/custom/*/manifest.json` to personas
- [x] Device TTS fallback for `macos_say` personas via `ELEVENLABS_DEFAULT_VOICE_ID`

### M6 — Reliability ✅

- [x] Retries + backoff for xAI
- [x] Structured error responses (`code`, `retryable`)
- [x] Deep `/health/ready` (xAI, Whisper, disk, personas, ElevenLabs)
- [x] Request ID through full pipeline

### M7 — Security

- [ ] Required `EMBER_DEVICE_TOKEN` in production mode
- [ ] Rate limiting per device/IP
- [ ] Secrets never logged

### M8 — Observability

- [ ] Structured JSON logging
- [ ] Per-request timing (STT / LLM / TTS ms)

### M9 — Packaging & Deploy

- [ ] Dockerfile + docker-compose
- [ ] launchd plist or systemd unit
- [ ] Graceful shutdown

### 1.0 Release Gate

M1–M6 complete, device API stable, Mac voice loop works end-to-end. Remaining gate items: M3 contract tests, M7–M9 (security, observability, packaging).

---

## Development Workflow

### First-time setup

```bash
cd /path/to/EmberForge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mac]"
cp .env.example .env   # optional if XAI_API_KEY is already exported
emberforge check
```

### Run the backend

```bash
emberforge serve
# or with auto-reload during development:
emberforge serve --reload
```

### Run tests

```bash
pytest
pytest -v tests/test_api.py
```

### Mac voice companion (full stack)

```bash
./start_ember.sh
./start_ember.sh --persona hal_9000
./start_ember.sh --text-only
```

### Verify device API (no hardware needed)

```bash
curl http://127.0.0.1:8000/device/v1/capabilities
curl http://127.0.0.1:8000/device/v1/personas
curl -X POST http://127.0.0.1:8000/device/v1/converse/text \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "persona": "ember", "device_id": "dev-001"}'
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_API_KEY` | — | xAI / Grok API key (**required**) |
| `GROK_API_KEY` | — | Legacy alias for `XAI_API_KEY` |
| `EMBER_HOST` | `127.0.0.1` | Server bind host |
| `EMBER_BACKEND_PORT` | `8000` | Server bind port |
| `EMBER_WHISPER_MODEL` | `base` | Server-side Whisper model |
| `EMBER_DEVICE_TOKEN` | — | Optional device bearer token |
| `EMBER_MAX_AUDIO_BYTES` | `1048576` | Max device audio upload |
| `EMBERFORGE_ROOT` | auto-detect | Project root override |
| `ELEVENLABS_API_KEY` | — | ElevenLabs TTS for device playback |
| `ELEVENLABS_DEFAULT_VOICE_ID` | — | Fallback voice for device TTS |
| `ELEVENLABS_MODEL` | `eleven_turbo_v2_5` | ElevenLabs model id |
| `EMBER_DEVICE_TTS_FALLBACK` | `true` | Use default voice for macos_say personas on devices |
| `XAI_MAX_RETRIES` | `3` | Retries for transient xAI failures |
| `XAI_RETRY_BASE_SECONDS` | `0.5` | Exponential backoff base delay for xAI |
| `ELEVENLABS_MAX_RETRIES` | `2` | Retries for transient ElevenLabs failures |
| `EMBER_HEALTH_DISK_MIN_BYTES` | `100000000` | Minimum free disk for `/health/ready` |
| `EMBER_MAC_TTS` | `macos_say` | Mac client TTS: `macos_say`, `elevenlabs`, or `auto` |

---

## API Surfaces

### Mac / developer

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Deep readiness (xAI, Whisper, disk) |
| GET | `/version` | Server + device API version |
| GET | `/personas` | Full persona list |
| POST | `/chat` | Text conversation |

### Consumer devices (stable)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/device/v1/capabilities` | Feature discovery on boot |
| GET | `/device/v1/personas` | Lightweight persona menu |
| POST | `/device/v1/converse/text` | Text-in conversation |
| POST | `/device/v1/converse` | WAV audio-in conversation |

Device contract documentation: `device/README.md`

---

## Versioning Policy

- **Server package:** semver in `emberforge/__init__.py` (currently `0.1.0`, targeting `1.0.0`)
- **Device API:** `/device/v1/` — breaking changes require `/device/v2/`
- Devices should call `/version` and `/device/v1/capabilities` on boot

---

## Current Version

| Component | Version |
|-----------|---------|
| Package | `0.1.0` |
| Device API | `v1` |
| Milestones complete | M1, M2, M3, M4, M5, M6 |

**Changelog:** [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog format)

**Next step:** M7 security (required device token in production, rate limiting).