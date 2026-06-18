"""Mac voice companion — uses shared STT/TTS providers + backend API."""

from __future__ import annotations

import asyncio
import base64
import os
import sys
import threading
import time
import uuid
from typing import Any

import requests

from emberforge.client.audio_playback import play_audio_bytes
from emberforge.client.ptt import PushToTalkSession, SessionEventType, clear_listening_indicator
from emberforge.client.recording import SAMPLE_RATE
from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.mac_say_tts import MacSayTTS
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
_speaking = False
_processing_turn = False
_turn_lock = threading.Lock()
_session_id = str(uuid.uuid4())


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


def reset_conversation(*, announce: bool = True) -> None:
    """Start a fresh multi-turn thread with the active persona."""
    global _session_id
    _session_id = str(uuid.uuid4())
    if announce:
        print("New conversation — prior context cleared.")


def select_persona(persona_id: str) -> bool:
    global _active_persona_id
    if persona_id not in _personas:
        print(f"Unknown persona '{persona_id}'.")
        print_persona_menu()
        return False
    if persona_id != _active_persona_id:
        reset_conversation(announce=False)
    _active_persona_id = persona_id
    active = _personas[persona_id]
    print(f"\nActive persona: {active['name']} ({persona_id}) — fresh conversation")
    return True


def transcribe_audio(audio) -> str | None:
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


def parse_quoted_prompt(raw: str) -> str | None:
    """Return inner text when input is a quoted prompt, e.g. \"Hal, close the cabin doors\"."""
    stripped = raw.strip()
    if len(stripped) < 2:
        return None
    if stripped[0] not in {'"', "'"} or stripped[-1] != stripped[0]:
        return None
    message = stripped[1:-1].strip()
    return message or None


def _use_backend_tts() -> bool:
    """ElevenLabs runs on the backend so speed/pronunciation settings apply."""
    return resolve_mac_tts_mode(_settings) == "elevenlabs"


def chat_with_persona(message: str, *, clear_history: bool = False) -> dict[str, Any]:
    payload = {
        "message": message,
        "persona": _active_persona_id,
        "session_id": _session_id,
        "clear_history": clear_history,
        "synthesize_audio": _use_backend_tts(),
    }
    response = requests.post(CHAT_URL, json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


def run_conversation_turn(user_input: str) -> None:
    global _speaking
    active_name = _personas[_active_persona_id]["name"]
    turn_hint = ""
    print(f"\n{active_name} is thinking...")
    result = chat_with_persona(user_input)
    turns = result.get("history_turns", 0)
    if turns > 1:
        turn_hint = f"  (turn {turns} in this conversation)"

    print("\n" + "=" * 60)
    print(f"{result['persona_name'].upper()}{turn_hint}:")
    print(result["response"])
    print("=" * 60 + "\n")

    _speaking = True
    try:
        speak_response(result["response"], result.get("voice", {}))
    finally:
        _speaking = False


def speak_response(text: str, voice_config: dict[str, Any]) -> None:
    audio_b64 = voice_config.get("audio_base64")
    if audio_b64:
        try:
            play_audio_bytes(
                base64.b64decode(audio_b64),
                voice_config.get("format") or "mp3",
            )
            return
        except (ValueError, OSError) as exc:
            print(f"Warning: could not play response audio ({exc}).")

    if voice_config.get("played_locally"):
        return

    mode = resolve_mac_tts_mode(_settings)
    voice = VoiceConfig.from_dict(voice_config)
    try:
        tts, resolved_voice = get_mac_tts_provider(voice, _settings)
        result = asyncio.run(tts.synthesize(text, resolved_voice))
        if result.audio_bytes:
            play_audio_bytes(result.audio_bytes, result.format or "mp3")
            return
        if result.played_locally:
            return
        print(f"Warning: no speech audio produced (TTS mode: {mode}).")
    except Exception as exc:
        print(f"Speech failed ({mode}): {exc}")
        if mode == "elevenlabs":
            _speak_macos_fallback(text, voice)


def _speak_macos_fallback(text: str, voice: VoiceConfig) -> None:
    print("Falling back to macOS say for this reply.")
    try:
        result = asyncio.run(MacSayTTS().synthesize(text, voice))
        if not result.played_locally:
            print("macOS say fallback did not produce audio.")
    except Exception as exc:
        print(f"macOS say fallback failed: {exc}")


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
    if cmd in {"clear", "new", "reset", "new conversation"}:
        reset_conversation()
        return "continue"
    if cmd in {"personas", "list"}:
        print_persona_menu()
        return "continue"
    if cmd.startswith("persona "):
        persona_id = cmd.split(maxsplit=1)[1].strip()
        select_persona(persona_id)
        return "continue"
    print(
        'Commands: persona <id>, personas, clear, quit — '
        'or a quoted prompt like "Hello HAL"'
    )
    return "continue"


def on_ptt_finished(duration: float) -> None:
    clear_listening_indicator(f"Captured {duration:.1f}s of audio.")


def process_command_line(raw: str) -> str:
    quoted = parse_quoted_prompt(raw)
    if quoted is not None:
        print(f'You typed: {quoted}')
        run_conversation_turn(quoted)
        return "continue"

    action = handle_command(raw.strip().lower())
    if action == "quit":
        return "quit"
    return action


def _can_accept_ptt() -> bool:
    return not _speaking and not _processing_turn


def _handle_audio_turn(audio) -> None:
    global _processing_turn
    with _turn_lock:
        if _processing_turn or _speaking:
            return
        _processing_turn = True
    try:
        user_input = transcribe_audio(audio)
        if user_input:
            run_conversation_turn(user_input)
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("message", "")
        except Exception:
            pass
        print(f"Backend error: {exc}{f' — {detail}' if detail else ''}")
    except Exception as exc:
        print(f"Turn failed: {exc}")
    finally:
        _processing_turn = False


def _read_command_line(session: PushToTalkSession, *, from_typing: bool) -> str | None:
    if not from_typing:
        session.enter_command_mode()
    try:
        if from_typing:
            return sys.stdin.readline()
        return input("> ")
    except EOFError:
        return None
    finally:
        session.leave_command_mode()
        session.clear_line_input_pending()


def _handle_command_input(session: PushToTalkSession, *, from_typing: bool = False) -> bool:
    """Return True when the session should continue."""
    raw = _read_command_line(session, from_typing=from_typing)
    if raw is None:
        return False

    if process_command_line(raw) == "quit":
        print(f"{_personas[_active_persona_id]['name']} signing off.")
        session.request_stop()
        return False
    return True


def run_session_loop(session: PushToTalkSession) -> None:
    while True:
        event = session.wait_event(timeout=0.1)
        if event is None:
            continue

        if event.type == SessionEventType.STOP:
            break

        if event.type == SessionEventType.AUDIO:
            if not _can_accept_ptt():
                continue
            threading.Thread(
                target=_handle_audio_turn,
                args=(event.audio,),
                name="emberforge-ptt-turn",
                daemon=True,
            ).start()
            continue

        if event.type in {SessionEventType.COMMAND, SessionEventType.TYPING}:
            if _processing_turn:
                print("Still processing the last turn — try again in a moment.")
                if event.type == SessionEventType.TYPING:
                    try:
                        sys.stdin.readline()
                    except EOFError:
                        pass
                    finally:
                        session.leave_command_mode()
                        session.clear_line_input_pending()
                continue
            from_typing = event.type == SessionEventType.TYPING
            if not _handle_command_input(session, from_typing=from_typing):
                break


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
        print("Tip: restart with ./start_ember.sh --elevenlabs for ElevenLabs playback on Mac.")

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
    print('Type a quoted prompt to skip the mic, e.g. "Hal, close the cabin doors"')
    print("Press Ctrl+C to exit.\n")

    session = PushToTalkSession(
        can_record=_can_accept_ptt,
        on_finished=on_ptt_finished,
    )
    print(
        f"Hold {session.ptt_key_label} to speak (max 30s). "
        "Conversation memory is on — say `clear` to start over."
    )
    session.start()

    try:
        run_session_loop(session)
    except KeyboardInterrupt:
        print("\n\nSigning off.")
        session.request_stop()
    finally:
        session.stop()


if __name__ == "__main__":
    main()