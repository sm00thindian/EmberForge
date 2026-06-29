# Firmware

Consumer-grade EmberForge devices run **thin client** firmware. All AI logic lives on the backend.

## Recommended hardware

**Waveshare ESP32-S3-AUDIO-Board** (Amazon [B0FPCNZS9M](https://www.amazon.com/dp/B0FPCNZS9M)) — pin map and config:

```bash
cd firmware/waveshare-esp32-s3-audio-board
cp config.h.example include/config.h
```

See [`waveshare-esp32-s3-audio-board/README.md`](waveshare-esp32-s3-audio-board/README.md) and [`docs/HARDWARE.md`](../docs/HARDWARE.md).

## Generic starter sketch

`esp32-voice-client/` — ESP32-S3 scaffold (raw I2S pins) that:

1. Connects to WiFi
2. Checks `/device/v1/capabilities`
3. Records audio on button press (you wire I2S hardware)
4. Uploads WAV to `/device/v1/converse`
5. Displays/plays the response

```bash
cp esp32-voice-client/config.h.example esp32-voice-client/config.h
# Edit WiFi + EMBER_HOST, then open in Arduino IDE or PlatformIO
```

## What the device does NOT do

- Hold xAI / Grok API keys
- Run Whisper or LLM inference
- Store persona prompts
- Clone voices

## Waveshare board (implemented)

`waveshare-esp32-s3-audio-board/` — full thin client with PlatformIO project:

| Component | Status |
|-----------|--------|
| WiFi + HTTP client | Done |
| Device API calls | Done |
| ES7210 mic → WAV upload | Done |
| ES8311 speaker ← MP3 reply | Done |
| VAD hands-free + hub wake phrase ("Hey Ember") | Done |
| TCA9555 persona + mic-mute keys | Done |
| WS2812 status ring | Done |
| OLED display | Not yet |

## Generic scaffold (`esp32-voice-client/`)

| Component | Status |
|-----------|--------|
| WiFi + HTTP client | Done |
| Device API calls | Done |
| I2S microphone recording | TODO in `recordWav()` |
| Speaker playback | TODO in `playResponse()` |
| OLED display | TODO in `playResponse()` |

See `device/README.md` for the full API contract.