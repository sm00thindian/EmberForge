# Phase 0: Mac Voice Companion

Talk to EmberForge on your Mac with local Whisper listening and swappable personas.

## Quick Start

```bash
./start_ember.sh                  # Interactive setup + Ember (default)
./start_ember.sh --persona hal_9000
./start_ember.sh --text-only      # Backend only (no microphone)
```

Requires `XAI_API_KEY` in `.env` or your shell. The start script can prompt for it on first run.

## During a Session

| Command | Action |
|---------|--------|
| ENTER | Start listening |
| `persona hal_9000` | Switch to HAL |
| `persona ember` | Switch back to Ember |
| `personas` | List available personas |
| `quit` | Exit |

## Personas

Personas combine a **system prompt** (personality) and a **voice profile** (how it sounds).

| ID | Voice (macOS `say`) |
|----|---------------------|
| `ember` | Shelley (English US), rate 155 |
| `hal_9000` | Daniel (UK), rate 145 |

Add more in `personas/*.json` + `prompts/personas/*.md`.

## Mac TTS Modes

Set in `.env`:

| `EMBER_MAC_TTS` | Behavior |
|-----------------|----------|
| `macos_say` | Default — free, uses system voices |
| `elevenlabs` | ElevenLabs MP3 playback (requires API key + voice ID) |
| `auto` | ElevenLabs when configured, otherwise `say` |

## Record a Custom Voice

For cloning with permission:

```bash
source ../.venv/bin/activate
python ../scripts/record_voice_sample.py --name kilynn
```

See [`voices/README.md`](../voices/README.md) for the full voice pipeline.

## Config (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_API_KEY` | — | **Required** — xAI / Grok |
| `EMBER_PERSONA` | `ember` | Starting persona |
| `EMBER_MAC_TTS` | `macos_say` | Mac playback engine |
| `EMBER_WHISPER_MODEL` | `base` | Whisper model size |
| `EMBER_BACKEND_PORT` | `8000` | Backend port |
| `ELEVENLABS_API_KEY` | — | Optional server/Mac TTS |
| `ELEVENLABS_DEFAULT_VOICE_ID` | — | ElevenLabs voice for fallback |
| `EMBER_INPUT_DEVICE` | (default) | Mic index or name |

## Manual Two-Terminal Setup

```bash
source .venv/bin/activate
pip install -e ".[dev,mac]"
emberforge serve --host 127.0.0.1 --port 8000

# new terminal
cd phase-0-brain && EMBER_PERSONA=hal_9000 python mac_voice_companion.py
```

See [`docs/RELEASE_1.0.md`](../docs/RELEASE_1.0.md) for the full 1.0 roadmap and [`CHANGELOG.md`](../CHANGELOG.md) for release notes.

---

**Status:** Mac voice companion with persona switching, improved macOS voices, and optional ElevenLabs playback path.