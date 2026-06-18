# EmberForge Voice Companion

**A personal AI voice companion with swappable personas, live context, and custom voices**  
*Talk to Ember on your Mac today. Configure your hub in the browser. Build the physical device tomorrow.*

[![Status](https://img.shields.io/badge/Status-1.0.0-blue)](.)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3%20(planned)-orange)](https://www.espressif.com/)
[![LLM](https://img.shields.io/badge/LLM-Grok%20%7C%20Claude-blue)](https://x.ai/)

> **v1.0.0** — Release 1.0 complete (M1–M9): production backend with setup UI, multi-turn memory, live context, security, structured logging, Docker/deploy packaging, and optional Claude LLM (Grok default). See [`CHANGELOG.md`](CHANGELOG.md) and [`docs/RELEASE_1.0.md`](docs/RELEASE_1.0.md).

---

## Vision

EmberForge is a **voice-first AI companion** you can actually talk to — not a text chatbot with speech bolted on.

The core experience is hearing a distinct personality speak back to you. That personality can be:

- **Ember** — your warm default companion (maker wisdom, music, honest conversation)
- **Character-inspired personas** — like a HAL 9000-style ship computer (fan-inspired, personal use)
- **Custom voices** — your own voice or someone else's, recorded with explicit permission and cloned via ElevenLabs

Eventually this runs on a **consumer-grade device** (ESP32-S3) on your desk or workbench. The device is a thin client — mic, speaker, button, display — while the EmberForge backend handles personas, STT, LLM, and TTS. Right now you prototype on Mac; the same backend serves hardware with zero API changes.

The backend is structured as a **portable hub**: maker/DIY defaults (local filesystem, `./start_ember.sh`, Docker on your LAN) with storage seams ready for hosted AWS deployment later. See [`docs/HUB_ARCHITECTURE.md`](docs/HUB_ARCHITECTURE.md).

---

## Quick Start (Mac)

**Prerequisites:** Python 3.10+, macOS for the voice client (backend-only works on Linux).

The fastest path from a fresh clone:

```bash
./start_ember.sh --text-only --open-setup
```

That script creates `.venv`, installs `.[dev,mac]`, picks or creates `.env`, prompts for a real `XAI_API_KEY` (placeholder values from `.env.example` are rejected), starts the backend, and opens the setup UI.

**Manual setup** (same result):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mac]"
cp .env.example .env          # replace your_xai_api_key_here with a real key
emberforge check
./start_ember.sh --text-only --open-setup
```

**Smoke test** after the hub is up:

1. Open [http://127.0.0.1:8000/setup](http://127.0.0.1:8000/setup) → Dashboard shows readiness.
2. **Test Chat** tab → send “Hello” → you get a text reply (and voice if ElevenLabs or macOS say is available).
3. `curl http://127.0.0.1:8000/health/ready` → `"status": "ok"` (or `"degraded"` if Whisper is not installed).

**Full voice mode:**

```bash
./start_ember.sh              # interactive setup + backend + voice companion
```

**Docker hub** (no Mac voice client; ElevenLabs TTS in browser):

```bash
cp .env.example .env && docker compose up --build -d
open http://127.0.0.1:8000/setup
```

See [`deploy/README.md`](deploy/README.md) for mounts, rebuilds, and production LAN binding.

**Setup website:** [http://127.0.0.1:8000/setup](http://127.0.0.1:8000/setup) — API keys, location, context, pairing, TOTP, and test chat with voice.

**Backend only:**

```bash
emberforge serve              # prints setup URL on startup
```

**Talk to HAL:**

```bash
./start_ember.sh --persona hal_9000
```

Switch personas mid-session: `persona hal_9000` or `persona ember` · `clear` starts a fresh conversation thread

---

## Configuration

Copy `.env.example` to `.env` and set at minimum:

| Variable | Required | Purpose |
|----------|----------|---------|
| `XAI_API_KEY` | Yes* | LLM API key for Grok (default provider) |
| `EMBER_LLM_PROVIDER` | No | `grok` (default) or `claude` |
| `ANTHROPIC_API_KEY` | Yes** | Required when `EMBER_LLM_PROVIDER=claude` |
| `EMBER_LLM_MODEL` | No | Model id (default `grok-3-latest` or `claude-sonnet-4-6`) |
| `EMBER_LOG_JSON` | No | Structured JSON logs for production (`true`) |
| `ELEVENLABS_API_KEY` | No | Server TTS for device API, setup test chat, optional Mac playback |
| `ELEVENLABS_DEFAULT_VOICE_ID` | No | Default ElevenLabs voice for device/Mac fallback |
| `EMBER_CONTEXT_ENABLED` | No | Inject weather, headlines, and profile once per session |
| `EMBER_RSS_FEEDS` | No | Comma-separated RSS URLs for headlines and news tools |
| `EMBER_TOOLS_ENABLED` | No | Let the LLM call weather/news tools on demand (default `true`) |

\* `XAI_API_KEY` required when provider is `grok` (default).  
\** `ANTHROPIC_API_KEY` required when provider is `claude`.

Switch to Claude in `.env` or the setup UI:

```bash
EMBER_LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Mac TTS mode (`macos_say`, `elevenlabs`, `auto`) is chosen per run via `./start_ember.sh` — not stored in `.env`.

Production security: `EMBER_ENV=production`, device pairing (`emberforge pair`), optional TOTP (`emberforge totp-setup`). See [`docs/M7_SECURITY.md`](docs/M7_SECURITY.md).

Full reference: [`docs/RELEASE_1.0.md`](docs/RELEASE_1.0.md#configuration-reference)

---

## Local Setup UI

Open **`/setup`** after starting the backend:

| Section | What it does |
|---------|----------------|
| **Dashboard** | Readiness, issues, RSS/context status |
| **API Keys** | Grok / Claude provider, API keys, LLM model |
| **Location & Context** | Geocode, user profile, RSS feeds |
| **Security & Devices** | Pairing codes, TOTP, revoke devices |
| **Test Chat** | Multi-turn chat with voice (ElevenLabs in browser or macOS say on hub) |

```bash
./start_ember.sh --text-only --open-setup
```

---

## Consumer Device Architecture

```
┌──────────────────────┐      WiFi       ┌─────────────────────────┐
│  ESP32-S3 Device     │ ◄────────────► │  EmberForge Backend      │
│  (thin client)       │                │  (Mac / home hub / VPS)  │
│                      │                │                          │
│  Button + mic        │  /device/v1/   │  Personas + Grok         │
│  Speaker + display   │  converse      │  Whisper STT + TTS       │
└──────────────────────┘                │  Setup UI at /setup      │
                                        └─────────────────────────┘
```

Consumer devices **never hold API keys or persona prompts**. They upload audio, receive a structured response (text + MP3 when ElevenLabs is configured), and play it back.

See [`device/README.md`](device/README.md) for the full contract and [`firmware/esp32-voice-client/`](firmware/esp32-voice-client/) for the starter sketch.

---

## Project Structure

```
EmberForge/
├── CHANGELOG.md
├── start_ember.sh              # Interactive Mac startup
├── .env.example                # Local configuration template
├── device/README.md            # Consumer device API contract
├── docs/
│   ├── HUB_ARCHITECTURE.md     # Maker-local hub, AWS migration path
│   ├── PHASE_0.md              # Mac companion exit criteria
│   ├── M7_SECURITY.md          # Pairing, TOTP, rate limits
│   └── RELEASE_1.0.md        # 1.0 milestone checklist
├── emberforge/                 # Python package (the backend)
│   ├── hub/                    # Composition root + storage protocols
│   ├── cli.py                  # serve | check | pair | totp-setup
│   ├── web/                    # Local setup SPA (/setup)
│   ├── services/               # personas, conversation, context, tools, voice
│   ├── client/                 # Mac voice companion + PTT
│   └── api/routes/             # health, chat, device, admin, setup
├── personas/                   # Persona definitions (personality + voice)
├── prompts/                    # System prompts + user_context.md
├── voices/custom/              # Recorded voice samples + consent
├── tests/                      # pytest suite (149 tests)
└── phase-0-brain/
    └── mac_voice_companion.py  # Thin Mac client entry point
```

---

## Personas

Personas are JSON files in `personas/`. Each defines a system prompt, voice profile, and temperature.

| ID | Name | Voice (Mac) |
|----|------|-------------|
| `ember` | Ember | Shelley (English US), rate 155 |
| `hal_9000` | HAL | Daniel (UK), rate 145 |

Add a persona: write a prompt in `prompts/`, create `personas/your_persona.json`, restart the backend.

---

## Voice Output

| Mode | How | Cost |
|------|-----|------|
| **Mac voice** (`./start_ember.sh`) | Hold **SPACE** to talk; macOS `say` by default | Free |
| **Mac ElevenLabs** (`./start_ember.sh --elevenlabs`) | ElevenLabs MP3 via `afplay` | ElevenLabs credits |
| **Setup test chat** | ElevenLabs in browser or macOS say on hub | Free / ElevenLabs |
| **Device API** | ElevenLabs MP3 in `voice.audio_base64` | ElevenLabs credits |

---

## Custom Voices (with permission)

```bash
source .venv/bin/activate
python scripts/record_voice_sample.py --name kilynn
```

Samples go to `voices/custom/<name>/samples/`. Link clones via `elevenlabs_voice_id` in `manifest.json`. **Only record voices you own or have explicit permission to use.**

---

## API

**Mac / developer:**

```bash
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/personas
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Good morning.", "persona": "hal_9000", "session_id": "my-session"}'
```

**Setup:**

```bash
curl http://127.0.0.1:8000/setup/v1/status
open http://127.0.0.1:8000/setup
```

**Consumer device:**

```bash
curl http://127.0.0.1:8000/device/v1/capabilities
emberforge pair   # issue pairing code for hardware
```

Errors return structured JSON: `code`, `message`, `retryable`, `request_id`.

---

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contributor guide.

```bash
source .venv/bin/activate
pip install -e ".[dev,mac]"     # [mac] for voice client + sounddevice tests
XAI_API_KEY=test-key pytest -v  # no live LLM key required
emberforge serve --reload
```

CI runs on **macOS** on every push to `main` (`.github/workflows/test.yml`).

---

## Current Status (June 2026)

| Area | Status |
|------|--------|
| **Package version** | **1.0.0** |
| **Release 1.0** (M1–M9) | ✅ complete |
| **Phase 0** Mac voice companion | ✅ complete |
| Local setup website (`/setup`) | ✅ |
| Multi-turn conversation memory | ✅ |
| Live context (weather, RSS, profile) | ✅ |
| On-demand weather/news tools | ✅ |
| M7 security (pairing, TOTP, rate limits) | ✅ |
| M8 observability (JSON logs, timing) | ✅ |
| M9 packaging (Docker, launchd, systemd) | ✅ |
| Claude LLM provider (Grok default) | ✅ |
| Device API `/device/v1/` + contract tests | ✅ |
| ElevenLabs server TTS | ✅ |
| ESP32 firmware scaffold | ✅ scaffold |

**Phase 0:** [`docs/PHASE_0.md`](docs/PHASE_0.md)  
**Deploy:** [`deploy/README.md`](deploy/README.md)

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md). Latest release: **[1.0.0](https://github.com/sm00thindian/EmberForge/releases/tag/v1.0.0)** (2026-06-17).

---

*EmberForge — Where voice, personality, and the maker's forge meet.*

*Maintained by: Kilynn Weber*