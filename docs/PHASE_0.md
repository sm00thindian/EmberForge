# Phase 0 — Mac Voice Companion ✅ Complete

**Completed:** June 2026  
**Scope:** Prove the full voice loop on Mac — listen, think, speak — with swappable personas, before consumer hardware.

Phase 0 is the **`phase-0-brain/`** Mac prototype. It shares the same backend and `/device/v1/` contract that ESP32 firmware will use later.

---

## Exit criteria (all met)

| Criterion | Status |
|-----------|--------|
| One-command Mac startup (`./start_ember.sh`) | ✅ |
| Backend + Mac client share `ConverseService` | ✅ |
| Push-to-talk microphone input (hold SPACE) | ✅ |
| Typed commands + `"quoted prompts"` without mic | ✅ |
| Local Whisper STT on Mac | ✅ |
| Persona switching (Ember, HAL) | ✅ |
| macOS `say` voices per persona | ✅ |
| Optional ElevenLabs playback on Mac (session flag) | ✅ |
| Flexible LLM model config (default Grok) | ✅ |
| Device API `/device/v1/` stable + schema contract tests (M3) | ✅ |
| pytest + GitHub Actions CI | ✅ |
| Multi-turn conversation memory (`session_id`) | ✅ |
| Local setup UI at `/setup` (v0.2.0) | ✅ |

---

## How to run

```bash
./start_ember.sh
./start_ember.sh --persona hal_9000
./start_ember.sh --text-only --open-setup   # hub + browser setup UI
./start_ember.sh --model grok-3-mini --elevenlabs
```

See [`phase-0-brain/README.md`](../phase-0-brain/README.md) for session controls and config.

---

## What Phase 0 is not

These are **Release 1.0+** or **hardware phases**, not Phase 0 blockers:

| Item | Track |
|------|-------|
| M7 security (device auth, pairing, TOTP, rate limits) | Complete — see [`M7_SECURITY.md`](M7_SECURITY.md) |
| M8 observability (JSON logs, timing) | Release 1.0 |
| M9 packaging (Docker, launchd, graceful shutdown) | Release 1.0 |
| ESP32 I2S mic / speaker / OLED firmware | Hardware |
| Custom voice cloning in the default voice loop | Voices pipeline |

---

## Contract tests (M3)

Device API response shapes are defined in JSON Schema:

```
device/schemas/v1/
├── capabilities.response.json
├── personas.response.json
├── converse.response.json
└── error.response.json
```

Validated in CI via `tests/test_device_contract.py`.

---

## Next step

**Release 1.0 gate:** M7 → M8 → M9. See [`RELEASE_1.0.md`](RELEASE_1.0.md).