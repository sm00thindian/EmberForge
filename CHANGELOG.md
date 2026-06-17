# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- (nothing yet)

## [0.2.0] - 2026-06-17

### Added

- **Local setup website** at `http://127.0.0.1:8000/setup` — API keys, location, user profile, RSS feeds, device pairing, TOTP, and test chat with voice playback
- Setup API (`/setup/v1/*`): status, masked config, location geocode, profile editor, TOTP secret generation
- Admin device management: `GET/DELETE /admin/v1/devices`
- **Multi-turn conversation memory** — `session_id` on `/chat` and device routes; continuation instructions to avoid re-greeting every turn
- **Live context** (weather, RSS headlines, user profile) injected once per voice session when `EMBER_CONTEXT_ENABLED=true`
- Interactive location setup via Open-Meteo geocoding (`emberforge serve` prompt + setup UI)
- **On-demand tools** (default on): `get_weather`, `get_headlines`, `search_news` with LLM tool loop
- M7 security: production device auth, per-device pairing (`emberforge pair`), TOTP admin sessions (`emberforge totp-setup`), rate limiting, log secret redaction
- Security guide [`docs/M7_SECURITY.md`](docs/M7_SECURITY.md)
- M3 device API contract tests (`tests/test_device_contract.py`) with JSON Schemas in `device/schemas/v1/`
- Phase 0 completion doc ([`docs/PHASE_0.md`](docs/PHASE_0.md))
- Flexible LLM configuration via `EMBER_LLM_MODEL`, `EMBER_LLM_API_URL`, and `EMBER_LLM_API_KEY` (OpenAI-compatible; defaults to Grok / xAI)
- Per-request and per-persona `model` overrides; `./start_ember.sh --model <id>` for session override
- Mac push-to-talk (hold **SPACE** to speak, tap **ENTER** for commands) aligned with future device button semantics
- `emberforge/client/ptt.py` keyboard session and refactored `record_while_active()` with 30s cap, trailing-silence fallback, and tap debounce
- `EMBER_PTT_KEY` env var to override the default Space PTT binding
- `emberforge` Python package with `emberforge serve`, `emberforge check`, `emberforge pair`, and `emberforge totp-setup`
- Central `Settings` via pydantic-settings
- FastAPI backend with Mac routes (`/chat`, `/personas`) and stable device API (`/device/v1/*`)
- Persona system with built-in `ember` and `hal_9000` personas
- Voice pipeline abstractions (`STTProvider`, `TTSProvider`, `ConverseService`)
- Local Whisper STT for Mac client and device audio uploads
- macOS `say` TTS for Mac voice mode with per-persona voice and rate settings
- ElevenLabs server-side TTS with MP3 output in device and chat responses (`voice.audio_base64`)
- Voice profile manifests under `voices/custom/` with consent tracking
- Mac voice client (`emberforge/client/mac_voice.py`) and `phase-0-brain/mac_voice_companion.py` shim
- Interactive `start_ember.sh` (env file selection, missing-key prompts, persona and mode selection, `--open-setup`)
- `EMBER_MAC_TTS` setting (`macos_say` | `elevenlabs` | `auto`) for Mac ElevenLabs playback
- Reliability layer: HTTP retries with backoff, structured API errors, request ID middleware
- Deep readiness endpoint at `/health/ready`
- pytest suite (120+ tests) and GitHub Actions CI on macOS
- Device integration guide (`device/README.md`) and ESP32-S3 firmware scaffold
- Voice sample recording script (`scripts/record_voice_sample.py`)
- Release 1.0 roadmap (`docs/RELEASE_1.0.md`)
- `.env.example` with starter RSS feeds and context/tool settings

### Changed

- Mac voice companion no longer uses double-ENTER listening; microphone input is hold-to-talk only
- `backend/main.py` is now a compatibility shim re-exporting `emberforge.api.app`
- Ember persona voice updated to `Shelley (English (US))` at rate 155 for smoother macOS speech
- HAL persona speech rate lowered to 145 for a calmer delivery
- `start_ember.sh` waits on `/health/ready` before launching the voice client; prints setup UI URL
- `POST /chat` accepts `synthesize_audio`, `play_audio`, and `session_id` for web test chat and tooling
- Locality removed from core Ember prompt; location comes from injected context when enabled

### Fixed

- Test Chat and Mac PTT now share multi-turn `session_id` memory (no more context loss between turns)
- Typing a quoted prompt or command no longer triggers PTT on space — first printable key enters text mode immediately
- Mac PTT no longer wedges the keyboard after the first turn
- PTT event loop stays responsive during Whisper/API/TTS by processing turns in a background thread
- Hodgen-style “City, State” geocoding via query variants and US state ranking
- `.env` shell sourcing fixed for quoted values (e.g. `EMBER_LOCATION_NAME`)
- News tools require `EMBER_RSS_FEEDS`; generic “news today” queries route to headlines
- Device route authentication no longer treats `Settings` as a request body field (422 on `/device/v1/converse/text`)
- ElevenLabs provider singleton refreshes when the API key changes
- API test fixture no longer recurses through a broken `create_chat_router` monkeypatch

## [0.1.0] - 2026-06-16

### Added

- Initial repository scaffolding and project vision documentation

[Unreleased]: https://github.com/sm00thindian/EmberForge/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sm00thindian/EmberForge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sm00thindian/EmberForge/releases/tag/v0.1.0