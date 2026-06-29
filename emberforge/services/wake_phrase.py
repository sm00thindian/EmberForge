"""Wake-phrase gating for hands-free device audio (e.g. \"Hey Ember\")."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from emberforge.services.personas import Persona

_LEADING_FILLERS = frozenset({"um", "uh", "so", "well", "like"})
_PARTIAL_WAKE_PREFIXES = frozenset({"hey", "hi", "hay", "okay", "ok"})
_COMMON_MISHEARINGS = {
    "ember": ("amber", "imber"),
    "hal": ("how", "pal"),
}


def normalize_transcript(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _strip_leading_fillers(normalized: str) -> str:
    words = normalized.split()
    while words and words[0] in _LEADING_FILLERS:
        words.pop(0)
    return " ".join(words)


def wake_phrases_for_persona(persona: Persona) -> tuple[str, ...]:
    """Return longest-first wake phrases for a persona."""
    names: set[str] = set()
    persona_id = persona.id.replace("_", " ").strip()
    persona_name = persona.name.strip().lower()
    if persona_id:
        names.add(persona_id)
    if persona_name:
        names.add(persona_name)
    if persona.id == "hal_9000":
        names.add("hal")

    phrases: set[str] = set()
    for name in names:
        for prefix in ("hey", "hi", "hay", "okay", "ok"):
            phrases.add(f"{prefix} {name}")
        for alias in _COMMON_MISHEARINGS.get(name.split()[0], ()):
            for prefix in ("hey", "hi", "hay"):
                phrases.add(f"{prefix} {alias}")

    return tuple(sorted(phrases, key=len, reverse=True))


@dataclass(frozen=True)
class WakePhraseMatch:
    matched: bool
    command: str
    phrase: str | None = None


def match_wake_phrase(transcript: str, persona: Persona) -> WakePhraseMatch:
    """Detect a wake phrase and return the remaining user command."""
    normalized = normalize_transcript(transcript)
    if not normalized:
        return WakePhraseMatch(False, "")

    candidates = (
        normalized,
        _strip_leading_fillers(normalized),
    )

    if normalized in _PARTIAL_WAKE_PREFIXES:
        return WakePhraseMatch(True, "", normalized)

    for candidate in candidates:
        if not candidate:
            continue
        for phrase in wake_phrases_for_persona(persona):
            if candidate == phrase:
                return WakePhraseMatch(True, "", phrase)
            prefix = f"{phrase} "
            if candidate.startswith(prefix):
                command = candidate[len(prefix) :].strip()
                return WakePhraseMatch(True, command, phrase)

            embedded = f" {phrase} "
            padded = f" {candidate} "
            idx = padded.find(embedded)
            if idx >= 0:
                command = padded[idx + len(embedded) :].strip()
                return WakePhraseMatch(True, command, phrase)

    return WakePhraseMatch(False, normalized)


class WakeSessionStore:
    """Per-device follow-up window after a successful wake phrase."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._armed_until: dict[str, float] = {}

    def is_armed(self, session_id: str, *, now: float | None = None) -> bool:
        if not session_id:
            return False
        current = time.monotonic() if now is None else now
        return self._armed_until.get(session_id, 0.0) > current

    def arm(self, session_id: str, *, now: float | None = None) -> None:
        if not session_id:
            return
        current = time.monotonic() if now is None else now
        self._armed_until[session_id] = current + self._ttl_seconds

    def disarm(self, session_id: str) -> None:
        self._armed_until.pop(session_id, None)