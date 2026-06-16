# EmberForge Voice Companion

**A personal AI voice companion with swappable personas and custom voices**  
*Talk to Ember on your Mac today. Build the physical device tomorrow.*

[![Status](https://img.shields.io/badge/Status-0.1.0%20(pre--release)-yellow)](.)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3%20(planned)-orange)](https://www.espressif.com/)
[![LLM](https://img.shields.io/badge/LLM-Grok%20%2F%20xAI%20API-blue)](https://x.ai/)

> **Pre-release:** Package version `0.1.0`. Milestones M1–M6 are complete; Release 1.0 gate is in progress. See [`CHANGELOG.md`](CHANGELOG.md) and [`docs/RELEASE_1.0.md`](docs/RELEASE_1.0.md).

---

## Vision

EmberForge is a **voice-first AI companion** you can actually talk to — not a text chatbot with speech bolted on.

The core experience is hearing a distinct personality speak back to you. That personality can be:

- **Ember** — your warm default companion (maker wisdom, music, honest conversation)
- **Character-inspired personas** — like a HAL 9000-style ship computer (fan-inspired, personal use)
- **Custom voices** — your own voice or someone else's, recorded with explicit permission and cloned via ElevenLabs

Eventually this runs on a **consumer-grade device** (ESP32-S3) on your desk or workbench. The device is a thin client — mic, speaker, button, display — while the EmberForge backend handles personas, STT, LLM, and TTS. Right now you prototype on Mac; the same backend serves hardware with zero API changes.

---

## Quick Start (Mac)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mac]"
cp .env.example .env          # add XAI_API_KEY (and optional ElevenLabs keys)
emberforge check              # validate config + personas
./start_ember.sh              # interactive setup + backend + voice companion
```

The start script creates the venv if needed, picks or creates `.env`, and prompts for missing configuration.

**Backend only:**

```bash
./start_ember.sh --text-only
# or
emberforge serve
```

**Talk to HAL:**

```bash
./start_ember.sh --persona hal_9000
```

Switch personas mid-session: `persona hal_9000` or `persona ember`

---

## Configuration

Copy `.env.example` to `.env` and set at minimum:

| Variable | Required | Purpose |
|----------|----------|---------|
| `XAI_API_KEY` | Yes | Grok / xAI LLM |
| `ELEVENLABS_API_KEY` | No | Server TTS for device API and optional Mac playback |
| `ELEVENLABS_DEFAULT_VOICE_ID` | No | Default ElevenLabs voice for device/Mac fallback |
| `EMBER_MAC_TTS` | No | `macos_say` (default), `elevenlabs`, or `auto` |

Full reference: [`docs/RELEASE_1.0.md`](docs/RELEASE_1.0.md#configuration-reference)

---

## Consumer Device Architecture

```
┌──────────────────────┐      WiFi       ┌─────────────────────────┐
│  ESP32-S3 Device     │ ◄────────────► │  EmberForge Backend      │
│  (thin client)       │                │  (Mac / home hub / VPS)  │
│                      │                │                          │
│  Button + mic        │  /device/v1/   │  Personas + Grok         │
│  Speaker + display   │  converse      │  Whisper STT + TTS       │
└──────────────────────┘                └─────────────────────────┘
```

Consumer devices **never hold API keys or persona prompts**. They upload audio, receive a structured response (text + MP3 when ElevenLabs is configured), and play it back.

See [`device/README.md`](device/README.md) for the full contract and [`firmware/esp32-voice-client/`](firmware/esp32-voice-client/) for the starter sketch.

---

## Project Structure

```
EmberForge/
├── CHANGELOG.md                # Keep a Changelog format
├── start_ember.sh              # Interactive Mac startup
├── .env.example                # Local configuration template
├── device/README.md            # Consumer device API contract
├── docs/RELEASE_1.0.md         # 1.0 milestone checklist
├── emberforge/                 # Python package (the backend)
│   ├── cli.py                  # emberforge serve | check
│   ├── settings.py             # Central configuration
│   ├── services/               # personas, conversation, voice, health
│   ├── client/                 # Mac voice companion + audio playback
│   └── api/routes/             # health, chat, device
├── personas/                   # Persona definitions (personality + voice)
├── prompts/                    # System prompts per persona
├── voices/custom/              # Recorded voice samples + consent
├── tests/                      # pytest suite
├── backend/main.py             # Compatibility shim
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

Add a persona: write a prompt in `prompts/personas/`, create `personas/your_persona.json`, restart the backend.

---

## Voice Output

| Mode | How | Cost |
|------|-----|------|
| **Mac voice** (`./start_ember.sh`) | macOS `say` by default | Free |
| **Mac ElevenLabs** (`EMBER_MAC_TTS=elevenlabs`) | ElevenLabs MP3 via `afplay` | ElevenLabs credits |
| **Device API** | ElevenLabs MP3 in `voice.audio_base64` | ElevenLabs credits |

Test ElevenLabs on Mac without the full voice loop:

```bash
curl -s -X POST http://127.0.0.1:8000/device/v1/converse/text \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","persona":"ember","device_id":"mac-test"}' \
  | python3 -c "import json,base64,tempfile,subprocess,sys; d=json.load(sys.stdin); p=tempfile.mktemp(suffix='.mp3'); open(p,'wb').write(base64.b64decode(d['voice']['audio_base64'])); subprocess.run(['afplay',p])"
```

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
  -d '{"message": "Good morning.", "persona": "hal_9000"}'
```

**Consumer device:**

```bash
curl http://127.0.0.1:8000/device/v1/capabilities
curl -X POST http://127.0.0.1:8000/device/v1/converse/text \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Ember", "persona": "ember", "device_id": "dev-001"}'
```

Errors return structured JSON: `code`, `message`, `retryable`, `request_id`.

---

## Development

```bash
source .venv/bin/activate
pytest -v
emberforge serve --reload
```

CI runs on push to `main` via GitHub Actions (`.github/workflows/test.yml`).

---

## Current Status (June 2026)

| Area | Status |
|------|--------|
| Mac voice companion + Whisper STT | ✅ |
| Persona system (Ember, HAL) | ✅ |
| `emberforge` package + CLI | ✅ |
| Device API `/device/v1/` | ✅ |
| ElevenLabs server TTS (device + optional Mac) | ✅ |
| Reliability (retries, errors, `/health/ready`) | ✅ |
| ESP32 firmware scaffold | ✅ scaffold |
| Release 1.0 gate (M7–M9) | ⏳ in progress |

**Next milestones:** M7 security, M8 observability, M9 packaging. See [`docs/RELEASE_1.0.md`](docs/RELEASE_1.0.md).

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for release history. Unreleased work is listed at the top; version `0.1.0` remains the last tagged baseline until Release 1.0.

---

*EmberForge — Where voice, personality, and the maker's forge meet.*

*Maintained by: Kilynn Weber*