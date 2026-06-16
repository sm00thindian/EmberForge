# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `emberforge` Python package with `emberforge serve`, `emberforge check`, and `python -m emberforge` entry points
- Central `Settings` via pydantic-settings (`XAI_API_KEY`, ElevenLabs, device API, retry, and health options)
- FastAPI backend with Mac routes (`/chat`, `/personas`) and stable device API (`/device/v1/*`)
- Persona system with built-in `ember` and `hal_9000` personas
- Voice pipeline abstractions (`STTProvider`, `TTSProvider`, `ConverseService`)
- Local Whisper STT for Mac client and device audio uploads
- macOS `say` TTS for Mac voice mode with per-persona voice and rate settings
- ElevenLabs server-side TTS with MP3 output in device responses (`voice.audio_base64`)
- Voice profile manifests under `voices/custom/` with consent tracking
- Mac voice client (`emberforge/client/mac_voice.py`) and `phase-0-brain/mac_voice_companion.py` shim
- Interactive `start_ember.sh` (env file selection, missing-key prompts, persona and mode selection)
- `EMBER_MAC_TTS` setting (`macos_say` | `elevenlabs` | `auto`) for future Mac ElevenLabs playback
- Reliability layer: HTTP retries with backoff, structured API errors, request ID middleware
- Deep readiness endpoint at `/health/ready`
- pytest suite (40+ tests) and GitHub Actions CI on macOS
- Device integration guide (`device/README.md`) and ESP32-S3 firmware scaffold
- Voice sample recording script (`scripts/record_voice_sample.py`)
- Release 1.0 roadmap (`docs/RELEASE_1.0.md`)
- `.env.example` for local configuration

### Changed

- `backend/main.py` is now a compatibility shim re-exporting `emberforge.api.app`
- Ember persona voice updated to `Shelley (English (US))` at rate 155 for smoother macOS speech
- HAL persona speech rate lowered to 145 for a calmer delivery
- `start_ember.sh` waits on `/health/ready` before launching the voice client

### Fixed

- Device route authentication no longer treats `Settings` as a request body field (422 on `/device/v1/converse/text`)
- ElevenLabs provider singleton refreshes when the API key changes
- API test fixture no longer recurses through a broken `create_chat_router` monkeypatch

## [0.1.0] - 2026-06-16

### Added

- Initial repository scaffolding and project vision documentation

[Unreleased]: https://github.com/sm00thindian/EmberForge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sm00thindian/EmberForge/releases/tag/v0.1.0