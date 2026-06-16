"""macOS built-in text-to-speech via the `say` command."""

from __future__ import annotations

import asyncio
import subprocess

from emberforge.services.personas import VoiceConfig
from emberforge.services.voice.base import TTSProvider, TTSResult


class MacSayTTS(TTSProvider):
    """Play speech through macOS `say`. Returns metadata only (no audio bytes)."""

    @property
    def name(self) -> str:
        return "macos_say"

    def available(self) -> bool:
        import shutil

        return shutil.which("say") is not None

    def produces_audio(self) -> bool:
        return False

    async def synthesize(self, text: str, voice: VoiceConfig) -> TTSResult:
        cleaned = text.replace("\n", " ").strip()
        if not cleaned:
            return TTSResult(
                provider=self.name,
                voice=voice.voice,
                rate=voice.rate,
                profile=voice.profile,
            )

        if self.available():
            await asyncio.to_thread(self._speak, cleaned, voice)

        return TTSResult(
            provider=self.name,
            voice=voice.voice,
            rate=voice.rate,
            profile=voice.profile,
            played_locally=self.available(),
        )

    def _speak(self, text: str, voice: VoiceConfig) -> None:
        cmd = ["say", "-v", voice.voice or "Samantha"]
        if voice.rate:
            cmd.extend(["-r", str(voice.rate)])
        cmd.append(text)
        subprocess.run(cmd, check=False)