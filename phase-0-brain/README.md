# Phase 0: EmberForge Digital Brain (Mac-first)

**Goal**: Build and run the intelligent "brain" of EmberForge on your Mac before building any hardware. This lets us iterate quickly on personality, creative capabilities, and voice interaction.

## What We Built

- Strong core **Ember** system prompt (warm digital ember personality + music + maker wisdom)
- FastAPI backend with `/chat` endpoint ready for Grok
- Simple Mac voice companion script that listens to your system microphone
- Clean project structure inside your Google Drive

## Folder Structure (in your Drive)

```
EmberForge_Companion/
├── phase-0-brain/
│   └── README.md (this file)
├── backend/
│   ├── main.py
│   └── requirements.txt
├── prompts/
│   └── ember_agent_prompt.md
└── mac_voice_companion.py
```

## Quick Start on Your Mac

### 1. Set up the backend

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your xAI / Grok API key
export GROK_API_KEY="your_actual_key_here"

# Run the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

Test it quickly:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Ember, tell me about yourself."}'
```

### 2. Talk to Ember with your voice (Mac microphone)

In a new terminal:

```bash
cd ..   # back to project root

python3 mac_voice_companion.py
```

- Press ENTER to start listening
- Speak clearly
- Ember will respond both in text and using your Mac's built-in voice

This gives you a working voice companion on your Mac today.

## Next Milestones (Phase 0 continuation)

1. **Improve STT quality** — Switch from Google STT to local Whisper (much better for creative work)
2. **Add TTS options** — ElevenLabs or local Piper / Coqui for higher quality voice
3. **Create specialized agents** — Music/Lyric Co-writer, Practical Maker, Personal Knowledge
4. **Add simple RAG** — Let Ember read your notes, song themes, or previous lyrics from files in the Drive

## Notes

- The current voice script uses free Google STT + macOS `say`. It works well for testing.
- All prompts live in the `prompts/` folder so they are easy to version and edit.
- The backend is designed so the future ESP32 hardware can call the exact same `/chat` endpoint.

This is the foundation. Once you're comfortable talking to Ember on your Mac, we can harden the voice pipeline and then move to hardware.

---

**Status**: Phase 0 foundation complete and running on Mac.  
Ready for voice improvements or specialized agents when you are.