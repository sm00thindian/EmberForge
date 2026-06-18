# Hardware — maker prototype

EmberForge consumer devices are **thin clients**. Intelligence stays on the hub; firmware only needs WiFi, PTT, mic, speaker, and optional display.

## Recommended first board

**Waveshare ESP32-S3-AUDIO-Board** — same product whether you buy from Waveshare or Amazon.

| Channel | Identifier |
|---------|------------|
| Amazon US | [B0FPCNZS9M](https://www.amazon.com/dp/B0FPCNZS9M) |
| Waveshare SKU | 32184 (with battery) / 32185-EN (without) |
| Product sticker | `Esp32-s3 Audio board` |

### Why this board

- Matches the architecture in [`device/README.md`](../device/README.md): ESP32-S3, WiFi, no on-device LLM
- **ES7210** dual mic + **ES8311** DAC/PA — integrated audio path (faster than breadboarding INMP441 + MAX98357)
- 8 MB PSRAM / 16 MB flash — enough for record buffers and MP3 decode
- Onboard PTT buttons (via TCA9555), RGB status ring, optional LCD/camera/battery
- ~$16–18 — strong maker/DIY entry point

### What to order

**Minimum**

1. ESP32-S3-AUDIO-Board (with or without bundled LiPo)
2. Small speaker for the onboard header
3. USB-C cable

**Skip for v0**

- OV5640 camera
- SPI LCD (add later for `display.lines`)
- TF card (hub streams TTS)

## Firmware target in this repo

```
firmware/waveshare-esp32-s3-audio-board/
  pins.h              # Pin + EXIO map
  config.h.example    # WiFi, hub URL, device token — copy to config.h
  README.md           # Bring-up checklist
```

Pin map and TCA9555 notes: [`firmware/waveshare-esp32-s3-audio-board/README.md`](../firmware/waveshare-esp32-s3-audio-board/README.md).

Generic HTTP scaffold (no ES8311 drivers): [`firmware/esp32-voice-client/`](../firmware/esp32-voice-client/).

## Hub pairing

1. Run hub: `./start_ember.sh` or `docker compose up -d`
2. `emberforge pair` → six-digit code → receive **device_token** (once)
3. Flash firmware with `EMBER_DEVICE_TOKEN` and hub LAN URL (`http://192.168.x.x:8000`)
4. Device calls `GET /device/v1/capabilities` on boot, then `POST /device/v1/converse` on PTT

See [`docs/M7_SECURITY.md`](M7_SECURITY.md).

## Prototype exit criteria

- [ ] WiFi joins home 2.4 GHz network
- [ ] Capabilities check succeeds against LAN hub
- [ ] Paired bearer token accepted (or dev mode without auth)
- [ ] Hold PTT → 16 kHz mono WAV uploaded
- [ ] Hub returns transcript + `response_text`
- [ ] `voice.audio_base64` MP3 plays on onboard speaker
- [ ] Second PTT turn remembers context (`session_id` = `device_id`)

## What we are not building yet

- Custom PCB / enclosure (prototype on Waveshare board first)
- On-device wake word or edge LLM (hub-side Whisper + LLM only)
- 5 GHz WiFi (ESP32 is 2.4 GHz only)

## Roadmap

Near-term firmware and hub work: [`ROADMAP.md`](ROADMAP.md).