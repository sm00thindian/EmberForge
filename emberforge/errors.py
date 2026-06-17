"""Structured application errors for API and service layers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmberForgeError(Exception):
    """Error with a stable code, HTTP status, and retry hint for clients."""

    code: str
    message: str
    status_code: int = 500
    retryable: bool = False
    request_id: str | None = None

    def to_dict(self, request_id: str | None = None) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "request_id": request_id or self.request_id,
        }


def config_error(message: str, request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("CONFIG_MISSING", message, 500, False, request_id)


def persona_not_found(persona_id: str, request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError(
        "PERSONA_NOT_FOUND",
        f"Unknown persona '{persona_id}'",
        404,
        False,
        request_id,
    )


def llm_error(message: str, *, retryable: bool = False, request_id: str | None = None) -> EmberForgeError:
    code = "LLM_UNAVAILABLE" if retryable else "LLM_ERROR"
    status = 503 if retryable else 502
    return EmberForgeError(code, message, status, retryable, request_id)


def stt_unavailable(message: str, request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("STT_UNAVAILABLE", message, 503, False, request_id)


def stt_no_speech(message: str = "No speech detected in audio", request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("STT_NO_SPEECH", message, 422, False, request_id)


def tts_error(message: str, *, retryable: bool = True, request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("TTS_ERROR", message, 503 if retryable else 502, retryable, request_id)


def audio_invalid(message: str, request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("AUDIO_INVALID", message, 400, False, request_id)


def audio_too_large(request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("AUDIO_TOO_LARGE", "Audio file too large", 413, False, request_id)


def unauthorized(message: str = "Unauthorized", request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError("UNAUTHORIZED", message, 401, False, request_id)


def rate_limited(request_id: str | None = None) -> EmberForgeError:
    return EmberForgeError(
        "RATE_LIMITED",
        "Too many requests. Slow down and try again.",
        429,
        True,
        request_id,
    )