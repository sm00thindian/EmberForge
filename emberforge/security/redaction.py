"""Redact secrets from strings and log records."""

from __future__ import annotations

import logging
import re
from re import Pattern

_SENSITIVE_ENV_KEYS = (
    "XAI_API_KEY",
    "GROK_API_KEY",
    "EMBER_LLM_API_KEY",
    "ELEVENLABS_API_KEY",
    "EMBER_DEVICE_TOKEN",
    "EMBER_ADMIN_TOKEN",
    "EMBER_ADMIN_TOTP_SECRET",
)

_BEARER_PATTERN: Pattern[str] = re.compile(
    r"(Bearer\s+)([A-Za-z0-9._\-+=]+)",
    re.IGNORECASE,
)
_KEY_VALUE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(rf"({key}\s*[=:]\s*)(\S+)", re.IGNORECASE) for key in _SENSITIVE_ENV_KEYS
)


def redact_secrets(text: str) -> str:
    """Replace likely secrets with placeholders."""
    if not text:
        return text

    redacted = _BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    for pattern in _KEY_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


class SecretRedactionFilter(logging.Filter):
    """Logging filter that redacts secrets from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True