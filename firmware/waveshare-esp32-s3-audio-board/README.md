# Waveshare ESP32-S3-AUDIO-Board — EmberForge thin client

Official maker prototype target for EmberForge hardware bring-up.

| Source | Link |
|--------|------|
| Amazon (US) | [B0FPCNZS9M](https://www.amazon.com/dp/B0FPCNZS9M) |
| Waveshare | [ESP32-S3-AUDIO-Board](https://www.waveshare.com/esp32-s3-audio-board.htm) |
| Wiki / demos | [waveshare.com/wiki/ESP32-S3-AUDIO-Board](https://www.waveshare.com/wiki/ESP32-S3-AUDIO-Board) |
| Repo hardware doc | [`docs/HARDWARE.md`](../../docs/HARDWARE.md) |

The sticker on the retail box reads **"Esp32-s3 Audio board"** — search that name for online docs if the Amazon title differs.

## What this board gives you

- ESP32-S3R8 (8 MB PSRAM, 16 MB flash)
- Dual mics (ES7210) with AEC/noise reduction
- Speaker path (ES8311 + PA) — matches hub MP3 (`voice.audio_base64`) playback work
- 3× user buttons via **TCA9555** expander (not direct GPIO)
- 7× WS2812 RGB ring on **GPIO38**
- Optional SPI LCD, DVP camera, TF card (skip for v0)

EmberForge uses this as a **thin client**: record WAV → `POST /device/v1/converse` → play MP3 reply. Ignore Waveshare’s on-device LLM / wake-word demos for the main product path.

## Files in this folder

| File | Purpose |
|------|---------|
| [`pins.h`](pins.h) | Full pin / EXIO map for firmware |
| [`config.h.example`](config.h.example) | WiFi, hub URL, device id, PTT selection — copy to `config.h` |

Application sketch: start from [`../esp32-voice-client/`](../esp32-voice-client/) HTTP layer + Waveshare wiki demos for ES7210/ES8311/TCA9555, or Waveshare’s `factory_01` / `mp3_play_03` ESP-IDF examples as the audio base.

## Quick bring-up

### 1. Hardware

1. Connect a small speaker to the onboard header (often not included in the box).
2. Power via USB-C. Use the **battery switch** only if you installed the optional LiPo.
3. For first flash: hold **BOOT**, plug USB, release BOOT if the serial port is missing.

### 2. Hub on your LAN

```bash
./start_ember.sh --text-only --open-setup
# or: docker compose up -d   (EMBER_DEPLOYMENT=docker)
emberforge pair
```

Note the **device token** (shown once) and your hub IP (e.g. `192.168.1.100`).

### 3. Firmware config

```bash
cd firmware/waveshare-esp32-s3-audio-board
cp config.h.example config.h
# Edit WIFI_*, EMBER_HOST, EMBER_BASE_URL, EMBER_DEVICE_TOKEN, EMBER_DEVICE_ID
```

### 4. Validate without custom audio (serial)

1. Flash any Waveshare WiFi example → confirm 2.4 GHz WiFi (ESP32 has no 5 GHz).
2. `GET http://<hub>:8000/device/v1/capabilities` with `Authorization: Bearer <token>`.
3. Confirm JSON includes `"hub": { "deployment": "local", ... }`.

### 5. Audio integration order

1. Init I2C (GPIO10/11) + **TCA9555** @ `0x20`.
2. Assert **EXIO9** (PA enable) before playback.
3. Bring up **ES7210** capture @ 16 kHz mono → WAV buffer.
4. Hold **EXIO10** (user key 1) for PTT → upload multipart `/device/v1/converse`.
5. Base64-decode `voice.audio_base64` → MP3 decode → **ES8311** play.

Recording limits: **12 s** cap, **1.5 s** trailing silence ([`device/README.md`](../../device/README.md)).

## TCA9555 / EXIO (important)

Pins labeled **EXIO** on the schematic are on the **TCA9555** expander, not ESP32 GPIO.

| EXIO | Typical function |
|------|------------------|
| EXIO9 | Power amplifier enable (enable before speaker) |
| EXIO10 | User key 1 — **EmberForge PTT** |
| EXIO11 | User key 2 |
| EXIO12 | User key 3 |
| EXIO4 | TF card CS |

Community references: [ESPHome voice YAML](https://github.com/sw3Dan/waveshare-s2-audio_esphome_voice), [arduino-audio-driver board def](https://github.com/pschatzmann/arduino-audio-driver/blob/main/src/ESP32S3AISmartSpeaker.h).

## I2S / codec pin summary

| Signal | GPIO | Chip |
|--------|------|------|
| I2C SCL | 10 | ES7210, ES8311, TCA9555, PCF85063 |
| I2C SDA | 11 | |
| I2S MCLK | 12 | shared |
| I2S BCLK | 13 | shared |
| I2S LRCK | 14 | shared |
| I2S mic data in | 15 | ES7210 ASDOUT |
| I2S spk data out | 16 | ES8311 DSDIN |
| RGB data | 38 | WS2812 ×7 |

## Optional add-ons (later)

- **1.47″ SPI LCD** — show `display.lines` from converse JSON
- **LiPo battery** — desk companion without USB cable
- **Camera** — not used by EmberForge v1 device API

## Related

- Device API: [`device/README.md`](../../device/README.md)
- Security / pairing: [`docs/M7_SECURITY.md`](../../docs/M7_SECURITY.md)
- Generic scaffold (pre-ES8310): [`../esp32-voice-client/`](../esp32-voice-client/)