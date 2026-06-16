# Consumer Device Integration

EmberForge is designed so **consumer-grade hardware stays simple** while the backend carries the intelligence.

## Architecture

```
┌─────────────────────────┐         WiFi          ┌──────────────────────────┐
│  Consumer Device        │ ◄──────────────────► │  EmberForge Backend       │
│  (ESP32-S3, etc.)       │                       │  (Mac, mini-PC, or hub)  │
│                         │                       │                          │
│  • Push-to-talk button  │   POST /device/v1/    │  • Persona engine        │
│  • Microphone           │        converse       │  • Grok / xAI LLM        │
│  • Speaker              │                       │  • Whisper STT           │
│  • Small display        │   GET  /device/v1/    │  • TTS (planned)         │
│  • WiFi only            │        personas       │  • Custom voice clones   │
└─────────────────────────┘                       └──────────────────────────┘
```

**The device never needs API keys, persona prompts, or LLM logic.** It records audio, uploads it, and plays/displays the response.

## Device API (stable contract)

All device endpoints live under `/device/v1/`. This version will remain backward-compatible as features are added.

| Endpoint | Purpose |
|----------|---------|
| `GET /device/v1/capabilities` | Check server features on boot |
| `GET /device/v1/personas` | List personas for a device menu |
| `POST /device/v1/converse` | Upload WAV audio → transcript + reply |
| `POST /device/v1/converse/text` | Send pre-transcribed text |

### Boot sequence (recommended)

1. Connect to WiFi
2. `GET /device/v1/capabilities` — confirm server is reachable and STT is available
3. `GET /device/v1/personas` — populate persona selector
4. On button press: record WAV → `POST /device/v1/converse` → play/display result

### Audio format

| Field | Value |
|-------|-------|
| Format | WAV |
| Encoding | 16-bit PCM (`pcm_s16le`) |
| Channels | Mono |
| Sample rate | 16 kHz preferred |

### Response shape

Every converse response returns the same JSON structure:

```json
{
  "request_id": "uuid",
  "transcript": "what the user said",
  "response_text": "persona reply",
  "persona": { "id": "ember", "name": "Ember" },
  "voice": {
    "provider": "macos_say",
    "format": null,
    "audio_url": null,
    "audio_base64": null
  },
  "display": {
    "title": "Ember",
    "lines": ["Short lines for", "small OLED screens"]
  },
  "timestamp": "2026-06-16T..."
}
```

When server-side TTS is enabled, `voice.audio_base64` or `voice.audio_url` will carry playable audio so the device can speak without local TTS.

## Device auth (optional)

Set `EMBER_DEVICE_TOKEN` on the backend. Devices send:

```
Authorization: Bearer <token>
```

If unset, the device API is open (fine for local dev on your LAN).

## Firmware scaffold

See `firmware/esp32-voice-client/` for a starter ESP32-S3 sketch that follows this contract.

## Deployment targets for the backend

The same backend runs on:

- **Your Mac** (development, Phase 0)
- **Home mini-PC / Raspberry Pi** (always-on home hub)
- **VPS** (remote access)

Consumer devices on the same network point at the hub's IP. The persona and voice experience is identical across Mac and hardware.