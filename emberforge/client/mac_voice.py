"""Mac voice companion — uses shared STT/TTS providers + backend API."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any

import requests

from emberforge.client.audio_playback import play_audio_bytes
from emberforge.client.recording import SAMPLE_RATE, record_until_silence
from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.registry import (
    get_mac_tts_provider,
    get_stt_provider,
    resolve_mac_tts_mode,
)
from emberforge.settings import Settings

BACKEND_URL = os.getenv("EMBER_BACKEND_URL", "http://localhost:8000").rstrip("/")
CHAT_URL = f"{BACKEND_URL}/chat"
PERSONAS_URL = f"{BACKEND_URL}/personas"
DEFAULT_PERSONA = os.getenv("EMBER_PERSONA", "ember")

_settings = Settings()
_personas: dict[str, dict[str, Any]] = {}
_active_persona_id = DEFAULT_PERSONA
_stt = get_stt_provider(_settings)


def wait_for_backend(timeout_seconds: float = 30.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def load_personas() -> dict[str, dict[str, Any]]:
    response = requests.get(PERSONAS_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    return {item["id"]: item for item in data["personas"]}


def print_persona_menu() -> None:
    print("\nAvailable personas:")
    for persona_id, persona in _personas.items():
        tagline = persona.get("tagline", "")
        inspired = persona.get("inspired_by")
        suffix = f" (inspired by {inspired})" if inspired else ""
        print(f"  - {persona_id}: {persona['name']} — {tagline}{suffix}")


def select_persona(persona_id: str) -> bool:
    global _active_persona_id
    if persona_id not in _personas:
        print(f"Unknown persona '{persona_id}'.")
        print_persona_menu()
        return False
    _active_persona_id = persona_id
    active = _personas[persona_id]
    print(f"\nActive persona: {active['name']} ({persona_id})")
    return True


def listen_from_microphone() -> str | None:
    audio = record_until_silence()
    if audio is None:
        return None

    if not _stt.available():
        print("Whisper STT is not available.")
        return None

    print("Transcribing with Whisper...")
    try:
        text = _stt.transcribe_array(audio, sample_rate=SAMPLE_RATE)
    except ValueError:
        print("Whisper did not pick up any words.")
        return None

    print(f"You said: {text}")
    return text


def chat_with_persona(message: str) -> dict[str, Any]:
    payload = {"message": message, "persona": _active_persona_id}
    response = requests.post(CHAT_URL, json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


def speak_response(text: str, voice_config: dict[str, Any]) -> None:
    voice = VoiceConfig.from_dict(voice_config)
    tts, resolved_voice = get_mac_tts_provider(voice, _settings)
    result = asyncio.run(tts.synthesize(text, resolved_voice))

    if result.audio_bytes:
        play_audio_bytes(result.audio_bytes, result.format or "mp3")


def describe_mac_tts_mode() -> str:
    configured = _settings.mac_tts_mode
    effective = resolve_mac_tts_mode(_settings)
    if configured == effective:
        return effective
    if configured == "elevenlabs" and effective == "macos_say":
        return f"{effective} (ElevenLabs not fully configured; set ELEVENLABS_API_KEY and ELEVENLABS_DEFAULT_VOICE_ID)"
    return f"{effective} (from {configured})"


def handle_command(cmd: str) -> str:
    if cmd in {"quit", "exit", "q"}:
        return "quit"
    if cmd in {"personas", "list"}:
        print_persona_menu()
        return "continue"
    if cmd.startswith("persona "):
        persona_id = cmd.split(maxsplit=1)[1].strip()
        select_persona(persona_id)
        return "continue"
    if cmd == "":
        return "listen"
    print("Commands: ENTER = talk, persona <id>, personas, quit")
    return "continue"


def main() -> None:
    global _personas, _active_persona_id

    print("=" * 60)
    print("EmberForge Voice Companion")
    print("Shared voice pipeline + persona backend")
    print("=" * 60)

    if _stt.available():
        print(f"STT provider: {_stt.name}")
    else:
        print("Warning: Whisper STT not available.")

    print(f"TTS mode: {describe_mac_tts_mode()}")
    if _settings.mac_tts_mode == "macos_say":
        print("Tip: set EMBER_MAC_TTS=elevenlabs in .env for ElevenLabs playback on Mac.")

    print("\nWaiting for backend...")
    if not wait_for_backend():
        print("Backend is not responding. Start with ./start_ember.sh")
        sys.exit(1)

    _personas = load_personas()
    if DEFAULT_PERSONA not in _personas:
        fallback = next(iter(_personas))
        print(f"Persona '{DEFAULT_PERSONA}' not found. Using '{fallback}'.")
        _active_persona_id = fallback
    else:
        _active_persona_id = DEFAULT_PERSONA

    select_persona(_active_persona_id)
    print_persona_menu()
    print("\nSwitch anytime with: persona hal_9000")
    print("Press Ctrl+C to exit.\n")

    while True:
        try:
            print("Press ENTER to speak, or type a command (personas / persona <id> / quit).")
            cmd = input("> ").strip().lower()
            action = handle_command(cmd)
            if action == "quit":
                print(f"{_personas[_active_persona_id]['name']} signing off.")
                break
            if action == "continue":
                continue

            user_input = listen_from_microphone()
            if not user_input:
                continue

            active_name = _personas[_active_persona_id]["name"]
            print(f"\n{active_name} is thinking...")
            result = chat_with_persona(user_input)

            print("\n" + "=" * 60)
            print(f"{result['persona_name'].upper()}:")
            print(result["response"])
            print("=" * 60 + "\n")

            speak_response(result["response"], result.get("voice", {}))

        except KeyboardInterrupt:
            print("\n\nSigning off.")
            break
        except Exception as exc:
            print(f"Unexpected error: {exc}")
            time.sleep(1)