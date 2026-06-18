# Phase 0: Mac Voice Companion ✅

Talk to EmberForge on your Mac with local Whisper listening and swappable personas.

**Phase 0 is complete** (June 2026). Exit criteria and what's next: [`docs/PHASE_0.md`](../docs/PHASE_0.md).

## Quick Start

```bash
./start_ember.sh                  # Interactive setup + Ember (default)
./start_ember.sh --persona hal_9000
./start_ember.sh --text-only --open-setup   # Backend + setup UI in browser
```

**Setup website:** http://127.0.0.1:8000/setup — keys, location, context, pairing, test chat.

Requires `XAI_API_KEY` in `.env` or your shell. The start script can prompt for it on first run.

## During a Session

| Input | Action |
|-------|--------|
| Hold **SPACE** | Push-to-talk — record while held (30s max) |
| Start typing | Enter text mode — spaces work in `"quoted prompts"` and commands |
| **ENTER** (tap) | Open command line when not typing yet |
| `persona hal_9000` | Switch to HAL |
| `persona ember` | Switch back to Ember |
| `personas` | List available personas |
| `clear` | Start a fresh conversation thread |
| `"quoted text"` | Skip mic — send a typed prompt |
| `quit` | Exit |

Override the PTT key with `EMBER_PTT_KEY` (`space`, `` ` ``, `f5`, or any single character).

macOS may prompt for **Accessibility** permission so the terminal can detect key hold/release.

## Personas

Personas combine a **system prompt** (personality) and a **voice profile** (how it sounds).

| ID | Voice (macOS `say`) |
|----|---------------------|
| `ember` | Shelley (English US), rate 155 |
| `hal_9000` | Daniel (UK), rate 145 |

Add more in `personas/*.json` + `prompts/personas/*.md`.

## Mac TTS Modes

Chosen each run via `./start_ember.sh` (interactive menu or flags):

| Flag / choice | Behavior |
|---------------|----------|
| default / `--macos-say` | Free — persona macOS voices |
| `--elevenlabs` | ElevenLabs MP3 playback |
| `--mac-tts auto` | ElevenLabs when configured, otherwise `say` |

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
| `XAI_API_KEY` | — | **Required** — LLM API key (Grok / xAI by default) |
| `EMBER_LLM_MODEL` | `grok-3-latest` | LLM model id |
| `EMBER_PERSONA` | `ember` | Starting persona |
| `EMBER_WHISPER_MODEL` | `base` | Whisper model size |
| `EMBER_BACKEND_PORT` | `8000` | Backend port |
| `ELEVENLABS_API_KEY` | — | Optional server/Mac TTS |
| `ELEVENLABS_DEFAULT_VOICE_ID` | — | ElevenLabs voice for fallback |
| `EMBER_INPUT_DEVICE` | (default) | Mic index or name |
| `EMBER_PTT_KEY` | `space` | Hold-to-talk key (`space`, `` ` ``, `f5`, …) |

## Manual Two-Terminal Setup

```bash
source .venv/bin/activate
pip install -e ".[dev,mac]"
emberforge serve --host 0.0.0.0 --port 8000
# localhost-only: emberforge serve --host 127.0.0.1 --port 8000

# new terminal
cd phase-0-brain && EMBER_PERSONA=hal_9000 python mac_voice_companion.py
```

See [`docs/RELEASE_1.0.md`](../docs/RELEASE_1.0.md) for the full 1.0 roadmap and [`CHANGELOG.md`](../CHANGELOG.md) for release notes.

---

**Status:** Phase 0 complete — PTT voice loop, personas, quoted prompts, flexible LLM, device API contract tests.