# Contributing to EmberForge

Thanks for helping improve EmberForge. This guide covers local development, testing, and what we expect in pull requests.

## Prerequisites

- **Python 3.10+** (3.12 recommended; matches CI)
- **macOS** for the full Mac voice client and `sounddevice`-based tests (optional on Linux — backend and API tests still run)
- **Docker** (optional) for hub-style deployment; see [`deploy/README.md`](deploy/README.md)

## First-time setup

```bash
git clone https://github.com/sm00thindian/EmberForge.git
cd EmberForge
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mac]"
cp .env.example .env    # replace your_xai_api_key_here with a real key for live LLM calls
emberforge check
```

The `[mac]` extra installs `sounddevice`, `requests`, and `pynput` for the Mac voice companion and related tests. Use `.[dev]` only if you are working on backend-only changes on a non-Mac machine.

## Running locally

**Recommended for new contributors** — backend + setup UI without voice hardware:

```bash
./start_ember.sh --text-only --open-setup
```

Other useful commands:

```bash
emberforge serve --reload          # API only, auto-reload on code changes
./start_ember.sh                   # full Mac voice companion (hold SPACE to talk)
./start_ember.sh --persona hal_9000
```

`./start_ember.sh` creates the venv, installs `.[dev,mac]`, validates config, and refuses placeholder API keys from `.env.example`.

## Tests

You do **not** need a live xAI key to run the test suite. Fixtures inject a fake key automatically:

```bash
source .venv/bin/activate
XAI_API_KEY=test-key pytest -v
```

Run a focused subset while iterating:

```bash
pytest tests/test_settings.py -v
pytest tests/test_setup_api.py -v
```

CI runs the full suite on **macOS** with `pip install -e ".[dev,mac]"` (see `.github/workflows/test.yml`).

## Docker development

For a production-like home hub:

```bash
cp .env.example .env
docker compose up --build -d
open http://127.0.0.1:8000/setup
```

Code under `emberforge/` is baked into the image — rebuild after backend changes (`docker compose up --build -d`). Mounts for `.env`, `prompts/`, and `personas/` apply on restart without rebuild. Details: [`deploy/README.md`](deploy/README.md).

## Project layout

| Path | Purpose |
|------|---------|
| `emberforge/` | Python backend (API, services, setup SPA) |
| `personas/` | Persona JSON definitions |
| `prompts/` | System prompts, user context, TTS pronunciations |
| `tests/` | pytest suite |
| `phase-0-brain/` | Thin Mac voice client entry |
| `device/` | Consumer device API contract |
| `firmware/` | ESP32 starter sketch |

See the [README](README.md#project-structure) for the full tree.

## Pull request checklist

1. **Tests pass** — `XAI_API_KEY=test-key pytest -v`
2. **Config still validates** — `emberforge check` (with a real or test key in `.env`)
3. **Focused diff** — one logical change per PR when possible
4. **Docs** — update README, `CHANGELOG.md`, or relevant `docs/` when behavior or config changes
5. **No secrets** — never commit `.env`, API keys, or voice samples without consent manifests

## Configuration notes

- **Grok (default):** set `XAI_API_KEY` in `.env`
- **Claude:** set `EMBER_LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY`
- **Placeholder keys:** `your_xai_api_key_here` from `.env.example` is rejected by `emberforge check`, `emberforge serve`, and `./start_ember.sh`
- **Tests vs production:** `EMBER_ENV=development` (default) keeps device pairing optional; see [`docs/M7_SECURITY.md`](docs/M7_SECURITY.md) for production

## Questions

Open a [GitHub issue](https://github.com/sm00thindian/EmberForge/issues) for bugs, feature ideas, or setup problems. Include your OS, Python version, and relevant log output (redact API keys).