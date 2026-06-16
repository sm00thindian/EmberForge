"""Local Whisper speech-to-text."""

from __future__ import annotations

import io
import wave

import numpy as np

from emberforge.settings import Settings


class WhisperSTT:
    """Transcribe audio with faster-whisper."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None

    @property
    def name(self) -> str:
        return "whisper"

    def available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )
        return self._model

    def _read_wav(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())

        if sample_width != 2:
            raise ValueError("Only 16-bit PCM WAV is supported")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        return audio, sample_rate

    def _resample(
        self,
        audio: np.ndarray,
        source_rate: int,
        target_rate: int = 16_000,
    ) -> np.ndarray:
        if source_rate == target_rate:
            return audio
        duration = len(audio) / source_rate
        target_length = int(duration * target_rate)
        source_times = np.linspace(0, duration, num=len(audio), endpoint=False)
        target_times = np.linspace(0, duration, num=target_length, endpoint=False)
        return np.interp(target_times, source_times, audio).astype(np.float32)

    def _transcribe(self, audio: np.ndarray) -> str:
        model = self._load_model()
        segments, _ = model.transcribe(audio, language="en", vad_filter=True, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise ValueError("No speech detected in audio")
        return text

    def transcribe_wav(self, audio_bytes: bytes) -> str:
        audio, sample_rate = self._read_wav(audio_bytes)
        audio = self._resample(audio, sample_rate)
        return self._transcribe(audio)

    def transcribe_array(self, audio: np.ndarray, sample_rate: int = 16_000) -> str:
        audio = self._resample(audio, sample_rate)
        return self._transcribe(audio)