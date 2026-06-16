# Voice Profiles

EmberForge separates **personality** (personas) from **voice output** (voice profiles).

## Voice Providers

| Provider | Status | Use case |
|----------|--------|----------|
| `macos_say` | **Active** | Built-in Mac TTS — instant, no API key |
| `recorded` | Scaffolded | Your recorded samples, used when cloning is wired up |
| `elevenlabs_clone` | **Active** | Cloned voices via ElevenLabs + consent manifest (create clone in ElevenLabs UI) |
| `elevenlabs` | **Active** | Preset ElevenLabs voices by `voice` id |

## Custom Voices (with permission)

Record voice samples for yourself or anyone who has **explicitly granted permission**.

```bash
./scripts/record_voice_sample.py --name kilynn
```

Samples are saved to `voices/custom/<name>/samples/`. A `manifest.json` tracks consent metadata.

**Never clone or use a voice without clear permission from the voice owner.**

## Folder Layout

```
voices/
├── README.md
└── custom/
    └── <voice_name>/
        ├── manifest.json    # consent + provider config
        └── samples/         # .wav recordings (gitignored)
```

## Linking a Voice to a Persona

Personas live in `personas/*.json`. Point the `voice` block at a provider:

```json
"voice": {
  "provider": "macos_say",
  "voice": "Daniel",
  "rate": 160
}
```

Link a cloned voice to a persona:

```json
"voice": {
  "provider": "elevenlabs_clone",
  "profile": "kilynn"
}
```

Set `elevenlabs_voice_id` in `voices/custom/kilynn/manifest.json` after creating the clone in ElevenLabs.

## Server TTS for devices

Set in `.env`:

```
ELEVENLABS_API_KEY=your_key
ELEVENLABS_DEFAULT_VOICE_ID=your_default_voice_id
```

Device API responses (`/device/v1/converse`) include `voice.audio_base64` (MP3) when ElevenLabs is configured. Personas using `macos_say` fall back to the default ElevenLabs voice for hardware playback.