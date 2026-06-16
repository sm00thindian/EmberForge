"""
EmberForge Phase 0 - Mac Voice Companion
Simple voice interface that listens to your Mac's microphone and talks to the Ember brain.

Requirements:
    pip install speechrecognition pyaudio

Run:
    python mac_voice_companion.py

Press ENTER to start listening, speak, then press ENTER again (or just wait for timeout).
"""

import speech_recognition as sr
import requests
import os
import time

BACKEND_URL = "http://localhost:8000/chat"

def speak(text: str):
    """Use macOS built-in voice for instant feedback (no API key needed)."""
    # You can change the voice with: say -v "Alex" "..."
    os.system(f'say "{text}"')

def listen_from_microphone():
    """Listen from the system microphone using speech_recognition."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("\n🎤 Adjusting for ambient noise... (please stay quiet for 2 seconds)")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)

    print("✅ Ready. Press ENTER to start listening (or Ctrl+C to quit).")
    input()

    print("🎙️  Listening... (speak now, then press ENTER when finished or wait for timeout)")
    with mic as source:
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)
        except sr.WaitTimeoutError:
            print("No speech detected. Try again.")
            return None

    print("⏳ Transcribing with system STT...")

    try:
        text = recognizer.recognize_google(audio)  # Free Google STT (works offline-ish)
        print(f"🗣️  You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Sorry, I didn't catch that clearly.")
        return None
    except sr.RequestError as e:
        print(f"STT service error: {e}")
        return None

def chat_with_ember(message: str, mode: str = "warm"):
    """Send message to the Ember backend."""
    try:
        payload = {
            "message": message,
            "mode": mode,
            "temperature": 0.75
        }
        response = requests.post(BACKEND_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "No response from Ember.")
    except Exception as e:
        return f"Error talking to Ember backend: {e}"

def main():
    print("=" * 60)
    print("EmberForge Phase 0 - Mac Voice Companion")
    print("Talk to Ember using your Mac's microphone")
    print("=" * 60)
    print("\nMake sure the backend is running: uvicorn main:app --reload")
    print("Press Ctrl+C at any time to exit.\n")

    while True:
        try:
            user_input = listen_from_microphone()
            if not user_input:
                continue

            print("\n🔥 Ember is thinking...")
            ember_response = chat_with_ember(user_input, mode="warm")

            print("\n" + "=" * 60)
            print("EMBER:")
            print(ember_response)
            print("=" * 60 + "\n")

            # Speak the response using macOS voice
            speak(ember_response)

            print("Press ENTER to speak again, or type 'quit' to exit.")
            cmd = input("> ").strip().lower()
            if cmd in ["quit", "exit", "q"]:
                print("Ember signing off. Stay warm.")
                break

        except KeyboardInterrupt:
            print("\n\nEmber signing off. Stay warm.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
