"""Text normalization before speech synthesis."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from emberforge.settings import Settings

_WORD_RE_TEMPLATE = r"\b{}\b"
_SENTENCE_BOUNDARY = re.compile(r'(?<=[a-z0-9])([.!?]+)(["\']?)(\s+)(?=[A-Z"\'])')


def _preserve_case(source: str, spoken: str) -> str:
    if source.isupper():
        return spoken.upper()
    if source.islower():
        return spoken.lower()
    if source[:1].isupper():
        if len(spoken) <= 1:
            return spoken.upper()
        return spoken[0].upper() + spoken[1:]
    return spoken


def apply_pronunciations(text: str, mapping: dict[str, str]) -> str:
    """Replace words for clearer TTS without changing on-screen chat text."""
    if not mapping:
        return text

    result = text
    for source, spoken in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        if not source or not spoken:
            continue
        pattern = re.compile(_WORD_RE_TEMPLATE.format(re.escape(source)), re.IGNORECASE)

        def repl(match: re.Match[str], *, _source=source, _spoken=spoken) -> str:
            return _preserve_case(match.group(0), _spoken)

        result = pattern.sub(repl, result)
    return result


@lru_cache
def load_pronunciation_map(project_root: str, relative_path: str) -> dict[str, str]:
    path = Path(project_root) / relative_path
    if not path.is_file():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"TTS pronunciations must be a JSON object: {path}")

    mapping: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"TTS pronunciation entries must be strings in {path}")
        key = key.strip()
        value = value.strip()
        if key and value:
            mapping[key] = value
    return mapping


def apply_sentence_pauses(text: str, pause_seconds: float) -> str:
    """Insert ElevenLabs SSML breaks between sentences for a more natural cadence."""
    if pause_seconds <= 0 or not text:
        return text
    if "<break" in text.lower():
        return text

    pause_tag = f'<break time="{pause_seconds:.2f}s" />'

    def repl(match: re.Match[str]) -> str:
        punct = match.group(1)
        quote = match.group(2)
        return f"{punct}{quote} {pause_tag} "

    return _SENTENCE_BOUNDARY.sub(repl, text)


def prepare_tts_text(text: str, settings: Settings) -> str:
    """Normalize text sent to TTS providers (pronunciation map, whitespace)."""
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        return ""

    mapping = load_pronunciation_map(
        str(settings.project_root),
        settings.tts_pronunciations_file,
    )
    return apply_pronunciations(cleaned, mapping)