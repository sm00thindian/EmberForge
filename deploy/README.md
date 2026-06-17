# EmberForge deployment (M9)

## Docker

```bash
cp .env.example .env   # configure keys
docker compose up --build -d
open http://127.0.0.1:8000/setup
```

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