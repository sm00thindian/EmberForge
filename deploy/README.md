# EmberForge deployment (M9)

Home-LAN hubs use **`EMBER_DEPLOYMENT=docker`** (set automatically in `docker-compose.yml`). Makers on Mac venv use `local` (default). Future AWS hosting uses `cloud` — see [`docs/HUB_ARCHITECTURE.md`](../docs/HUB_ARCHITECTURE.md) and [`docs/ROADMAP.md`](../docs/ROADMAP.md).

## Docker (recommended home hub)

### First run

```bash
cp .env.example .env   # add XAI_API_KEY, ElevenLabs, etc.
docker compose up --build -d
open http://127.0.0.1:8000/setup
# LAN (same Wi‑Fi): http://<hub-ip>:8000/setup
```

### What is mounted

| Host path | Container | Purpose |
|-----------|-----------|---------|
| `.env` | `/app/.env` | **Source of truth** for secrets and settings; setup UI saves here |
| `personas/` | `/app/personas` | Persona definitions (read-only) |
| `prompts/` | `/app/prompts` | System prompts, `user_context.md`, TTS pronunciations |
| `voices/` | `/app/voices` | Custom voice manifests |
| *(named volume)* | `/app/.emberforge` | Pairing, devices, TOTP state |

The Python package (`emberforge/`) is **baked into the image**. Rebuild after code changes:

```bash
docker compose up --build -d
```

Edits under `prompts/`, `personas/`, or `.env` apply after a restart — no rebuild:

```bash
docker compose restart
```

### Typical workflow

1. **Configure** — edit host `.env` or use `/setup` (writes the same file).
2. **Rebuild** — when you `git pull` backend changes: `docker compose up --build -d`.
3. **Mac voice** — `./start_ember.sh` on your Mac; it talks to `http://127.0.0.1:8000` (or set `EMBER_BACKEND_URL` to the hub LAN IP from another machine).

### Production on LAN

```bash
# .env
EMBER_ENV=production
EMBER_HOST=0.0.0.0
EMBER_ADMIN_TOTP_SECRET=...   # required for remote /chat; see docs/M7_SECURITY.md
```

Setup **writes** (save keys, location, pairing) stay localhost-only in production. LAN clients can view status; use TOTP for remote admin.

### Logs and health

```bash
docker compose logs -f emberforge
curl http://127.0.0.1:8000/health/ready
```

---

## macOS launchd

1. Edit `deploy/emberforge.plist` — replace `/path/to/EmberForge` with your install path.
2. `mkdir -p logs`
3. `cp deploy/emberforge.plist ~/Library/LaunchAgents/com.emberforge.backend.plist`
4. `launchctl load ~/Library/LaunchAgents/com.emberforge.backend.plist`

## Linux systemd

1. Install EmberForge to `/opt/emberforge` with a dedicated `emberforge` user.
2. `sudo cp deploy/emberforge.service /etc/systemd/system/`
3. `sudo systemctl daemon-reload`
4. `sudo systemctl enable --now emberforge`

Graceful shutdown: `emberforge serve` runs under uvicorn; SIGTERM drains in-flight requests (default timeout 30s in systemd unit).