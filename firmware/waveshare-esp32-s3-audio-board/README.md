# Waveshare ESP32-S3-AUDIO-Board — EmberForge thin client

Official maker prototype target for EmberForge hardware bring-up.

| Source | Link |
|--------|------|
| Amazon (US) | [B0FPCNZS9M](https://www.amazon.com/dp/B0FPCNZS9M) |
| Waveshare | [ESP32-S3-AUDIO-Board](https://www.waveshare.com/wiki/ESP32-S3-AUDIO-Board) |
| Wiki / demos | [waveshare.com/wiki/ESP32-S3-AUDIO-Board](https://www.waveshare.com/wiki/ESP32-S3-AUDIO-Board) |
| Repo hardware doc | [`docs/HARDWARE.md`](../../docs/HARDWARE.md) |

The sticker on the retail box reads **"Esp32-s3 Audio board"** — search that name for online docs if the Amazon title differs.

## What this board gives you

- ESP32-S3R8 (8 MB PSRAM, 16 MB flash)
- Dual mics (ES7210) with AEC/noise reduction
- Speaker path (ES8311 + PA) — plays hub MP3 (`voice.audio_base64`)
- 3× user buttons via **TCA9555** expander (not direct GPIO)
- 7× WS2812 RGB ring on **GPIO38**
- Optional SPI LCD, DVP camera, TF card (skip for v0)

EmberForge uses this as a **thin client**: record WAV → `POST /device/v1/converse` → play MP3 reply.

## Firmware in this folder

| Path | Purpose |
|------|---------|
| [`platformio.ini`](platformio.ini) | Build target (ESP32-S3, 16 MB flash, OPI PSRAM) |
| [`src/main.cpp`](src/main.cpp) | Boot, VAD/PTT loop, persona + mic-mute keys |
| [`src/ember_api.cpp`](src/ember_api.cpp) | WiFi + `/device/v1/*` HTTP client |
| [`src/ember_audio.cpp`](src/ember_audio.cpp) | ES7210/ES8311 via `ESP32S3AISmartSpeaker` |
| [`src/ember_status_led.cpp`](src/ember_status_led.cpp) | WS2812 ring states |
| [`pins.h`](pins.h) | Pin / EXIO map + VAD timing |
| [`config.h.example`](config.h.example) | WiFi + hub URL — copy to `include/config.h` |

Audio drivers use [arduino-audio-tools](https://github.com/pschatzmann/arduino-audio-tools) + [arduino-audio-driver](https://github.com/pschatzmann/arduino-audio-driver) (`ESP32S3AISmartSpeaker` board definition — same silicon as this Waveshare board).

### How to talk (`EMBER_TRIGGER_MODE` in `include/config.h`)

| Mode | What you do |
|------|-------------|
| `EMBER_TRIGGER_VAD` (recommended) | Hands-free — say **"Hey Ember"** then your question |
| `EMBER_TRIGGER_PTT_BOOT` | Hold the **BOOT** button (labeled, near USB) while speaking |
| `EMBER_TRIGGER_PTT_KEY1` | Hold tiny **user key 1** (SMD button on board edge) |

**"Hey Ember" wake phrase** is enforced on the **hub** (Whisper STT + phrase matching), not on-device. The device listens continuously in VAD mode; only utterances that include the wake phrase (or fall within the follow-up window) get an LLM reply.

**Examples:**

- *"Hey Ember, what's the weather?"* — one utterance
- *"Hey Ember"* … pause … *"what time is it?"* — two utterances within the hub follow-up window (default 90s)
- Background conversation without "Hey Ember" — silently ignored (cyan LED, no reply)

| Button | Action |
|--------|--------|
| **BOOT** (GPIO0) | PTT when `EMBER_TRIGGER_PTT_BOOT` |
| **Key 2** (4th from USB) | Cycle persona (ring flashes **blue** twice) |
| **Key 3** (5th from USB, rightmost user key) | Toggle mic mute (amber pulse = off) |

Edge buttons left → right from USB-C:

```text
[1 RESET] [2 BOOT] [3 KEY1] [4 KEY2] [5 KEY3]
```

Waveshare prints EXIO9 / EXIO10 / EXIO11 on the schematic, but those labels do not always match which line is wired to each physical button. EmberForge names buttons by position from USB (**Key 1–3**). Mic mute is **Key 3** in docs and firmware (`getKey(1)` in the audio driver).

### RGB ring states

| Color | Meaning |
|-------|---------|
| Cyan | Listening (VAD hands-free) |
| Amber pulse | Mic muted |
| Red | Recording speech |
| Purple | Uploading to hub |
| Green | Playing reply |
| Blue flash (×2) | Persona switched |

## Flash and run

### 1. Hub on your LAN

```bash
cd /path/to/EmberForge
emberforge serve --host 0.0.0.0 --port 8000
# Or: ./start_ember.sh --non-interactive --text-only
```

Hub should be reachable at `http://<your-mac-lan-ip>:8000`. Set a **real** `XAI_API_KEY` in `.env` (placeholder values cause LLM failures).

Configure ElevenLabs in `.env` for spoken device replies (`ELEVENLABS_API_KEY` + per-persona voice ids in `personas/*.json`).

### 2. Configure firmware

```bash
cd firmware/waveshare-esp32-s3-audio-board
cp config.h.example include/config.h
```

Edit `include/config.h`:

- `WIFI_SSID` / `WIFI_PASSWORD` — **2.4 GHz** network only
- `EMBER_BASE_URL` — e.g. `http://192.168.1.119:8000`
- `EMBER_DEVICE_ID` — unique per unit (used as `session_id` on the hub)
- `EMBER_TRIGGER_MODE` — `EMBER_TRIGGER_VAD` for hands-free + wake phrase
- Optional: `EMBER_DEVICE_TOKEN` after `emberforge pair`

### 3. Build and upload (PlatformIO)

```bash
pip install platformio   # once
pio run -e waveshare-audio-full -t upload
pio device monitor
```

USB port on macOS is usually `/dev/cu.usbmodem101`. If upload fails, hold **BOOT**, plug USB, release BOOT.

### 4. Arduino IDE (alternative)

Install libraries: **arduino-audio-tools**, **arduino-audio-driver**, **arduino-libhelix**, **ArduinoJson**, **Adafruit NeoPixel**.

Copy all `src/*.cpp`, `include/*.h`, `pins.h`, and `include/config.h` into one sketch folder, or open this directory with the [PlatformIO IDE extension](https://platformio.org/install/ide/vscode).

Board settings: **ESP32S3 Dev Module**, USB CDC On Boot **Enabled**, PSRAM **OPI**, Flash **16 MB**.

## Boot sequence

1. WiFi join
2. `GET /device/v1/capabilities`
3. `GET /device/v1/personas` — sets active persona (Key 2 cycles)
4. VAD captures speech → `POST /device/v1/converse` → play `voice.audio_base64` MP3

Recording limits (see [`pins.h`](pins.h)): **12 s** max, **2.2 s** trailing silence after speech ends, **0.35 s** minimum speech.

## Hub tuning (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMBER_DEVICE_WAKE_PHRASE_ENABLED` | `true` | Require "Hey Ember" (or persona name) before replying |
| `EMBER_DEVICE_WAKE_PHRASE_TIMEOUT_SECONDS` | `90` | Follow-up window after wake phrase |
| `EMBER_DEVICE_TOOLS_ENABLED` | `false` | Skip on-demand tool round-trips for lower latency |
| `EMBER_DEVICE_MAX_TOKENS` | `280` | Shorter device replies |
| `ELEVENLABS_SPEED` | `0.9` | Speech rate (1.0 = normal) |
| `ELEVENLABS_SENTENCE_PAUSE_SECONDS` | `0.4` | Pause between sentences in TTS |

## TCA9555 / EXIO (important)

Pins labeled **EXIO** on the schematic are on the **TCA9555** expander, not ESP32 GPIO.

| EXIO | Typical function |
|------|------------------|
| EXIO9 | PA enable (not a button input) |
| EXIO10 / EXIO11 / EXIO12 | User keys via TCA9555 — see `pins.h` driver indices |

**EmberForge key map (use these names):**

| EmberForge | Position from USB | Function |
|------------|-------------------|----------|
| Key 1 | 3rd button | (PA / not used as input) |
| Key 2 | 4th button | Persona cycle |
| Key 3 | 5th button | **Mic mute** |

## Related

- Device API: [`device/README.md`](../../device/README.md)
- Security / pairing: [`docs/M7_SECURITY.md`](../../docs/M7_SECURITY.md)
- Generic scaffold (pre-ES8310): [`../esp32-voice-client/`](../esp32-voice-client/)