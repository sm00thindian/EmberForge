# Release 1.0 — EmberForge Backend

**Target:** A production-quality backend, fully developable and testable on Mac, with a stable API for consumer-grade devices.

Release 1.0 is the **server software only** — not the ESP32 firmware. A **local setup UI** at `/setup` (shipped in v0.2.0) handles hub configuration; consumer devices stay thin clients. The backend is the brain that Mac clients and physical devices talk to.

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
│   ├── conversation.py  # Grok / Claude conversation engine
│   └── stt.py           # Server-side Whisper (device uploads)
└── api/
    ├── app.py           # FastAPI factory
    └── routes/
        ├── health.py    # /health, /version
        ├── chat.py      # /chat, /personas (Mac)
        └── device.py    # /device/v1/* (hardware)
```

**Principle:** Mac and devices share `services/conversation.py` and `ConverseService`. Clients differ in input path (local Whisper vs uploaded WAV) and output rendering (macOS `say`, optional ElevenLabs on Mac via `start_ember.sh`, or server MP3 for devices).

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

### M3 — Tests & CI ✅

- [x] pytest suite (settings, personas, conversation, API)
- [x] GitHub Actions CI workflow (`.github/workflows/test.yml`)
- [x] Contract tests for `/device/v1/` response shape (JSON schema in `device/schemas/v1/`)

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

### M7 — Security ✅

- [x] Required device auth in production (`EMBER_DEVICE_TOKEN` or paired devices)
- [x] Device pairing flow (`emberforge pair` → `/device/v1/pair/confirm`)
- [x] Remote admin auth (TOTP session + static token; localhost trusted)
- [x] Rate limiting per device/IP
- [x] Secrets never logged
- [x] Security guide: [`M7_SECURITY.md`](M7_SECURITY.md)
- [x] Local setup UI for pairing, TOTP, and device revoke (`/setup`, `/admin/v1/devices`)

### Post–Phase 0 features (v0.2.0) ✅

- [x] Multi-turn conversation memory (`session_id`, `EMBER_CONVERSATION_*`)
- [x] Live context (weather, RSS, `prompts/user_context.md`)
- [x] On-demand LLM tools (`get_weather`, `get_headlines`, `search_news`)
- [x] Local setup website (`emberforge/web/`, `/setup/v1/*`)

### M8 — Observability ✅

- [x] Structured JSON logging (`EMBER_LOG_JSON=true`, `emberforge/observability/logging.py`)
- [x] Per-request timing (STT / LLM / TTS ms via `ObservabilityMiddleware`, `X-Timing-*` headers)

### M9 — Packaging & Deploy ✅

- [x] Dockerfile + docker-compose
- [x] launchd plist or systemd unit (`deploy/emberforge.plist`, `deploy/emberforge.service`)
- [x] Graceful shutdown (FastAPI lifespan + uvicorn SIGTERM drain)

### LLM provider switch (v1.0.0) ✅

- [x] `EMBER_LLM_PROVIDER=grok` (default) or `claude`
- [x] Claude via Anthropic OpenAI-compatible API (`ANTHROPIC_API_KEY`, default model `claude-sonnet-4-6`)
- [x] Setup UI provider dropdown

### 1.0 Release Gate ✅

M1–M9 complete, M3 contract tests complete, device API stable, Mac voice loop works end-to-end (**Phase 0 complete** — see [`PHASE_0.md`](PHASE_0.md)). **Release 1.0 shipped as package version `1.0.0`.**

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
| `XAI_API_KEY` | — | LLM API key (**required** for default xAI / Grok) |
| `GROK_API_KEY` | — | Legacy alias for `XAI_API_KEY` |
| `EMBER_LLM_PROVIDER` | `grok` | `grok` or `claude` |
| `ANTHROPIC_API_KEY` | — | Required when `EMBER_LLM_PROVIDER=claude` |
| `EMBER_LLM_MODEL` | `grok-3-latest` | LLM model id (`claude-sonnet-4-6` when provider is Claude) |
| `EMBER_LLM_API_URL` | provider default | OpenAI-compatible chat endpoint |
| `EMBER_LLM_API_KEY` | — | Optional separate LLM key (falls back to provider key) |
| `EMBER_LOG_JSON` | `false` | Emit structured JSON logs (recommended in production) |
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
| `EMBER_CONTEXT_ENABLED` | `false` | Weather + RSS + profile per session |
| `EMBER_LAT` / `EMBER_LON` | — | Coordinates for weather context |
| `EMBER_RSS_FEEDS` | — | Comma-separated RSS URLs |
| `EMBER_TOOLS_ENABLED` | `true` | On-demand weather/news tools |
| `EMBER_CONVERSATION_MAX_TURNS` | `20` | Multi-turn memory per `session_id` |
| `EMBER_ENV` | `development` | `production` enables device auth + rate limits |

Mac TTS mode is **not** in `.env` — use `./start_ember.sh` interactively or `--macos-say` / `--elevenlabs` / `--mac-tts auto`.

---

## API Surfaces

### Mac / developer

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Deep readiness (xAI, Whisper, disk) |
| GET | `/version` | Server + device API version |
| GET | `/setup` | Local setup SPA |
| GET | `/setup/v1/status` | Hub readiness for setup UI |
| GET | `/personas` | Full persona list |
| POST | `/chat` | Text conversation (`session_id`, optional TTS flags) |

### Admin / setup (localhost write in production)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/admin/v1/pair/code` | Issue device pairing code |
| GET | `/admin/v1/devices` | List paired devices |
| DELETE | `/admin/v1/devices/{id}` | Revoke a device |
| GET | `/admin/v1/totp/setup` | TOTP provisioning URI |
| PATCH | `/setup/v1/config` | Update `.env` from setup UI |

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

- **Server package:** semver in `emberforge/__init__.py` (currently `1.0.0`)
- **Device API:** `/device/v1/` — breaking changes require `/device/v2/`
- Devices should call `/version` and `/device/v1/capabilities` on boot

---

## Current Version

| Component | Version |
|-----------|---------|
| Package | `1.0.0` |
| Device API | `v1` |
| Milestones complete | M1–M9 (incl. M3 device contract tests) |
| Phase 0 (Mac companion) | ✅ Complete — [`PHASE_0.md`](PHASE_0.md) |
| Local setup UI | ✅ `/setup` |
| LLM providers | Grok (default), Claude |
| Deploy | Docker, launchd, systemd — [`deploy/README.md`](../deploy/README.md) |

**Changelog:** [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog format)

**Release 1.0 complete.** Next work: consumer device firmware and hub hardening beyond 1.0.