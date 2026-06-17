"""Per-request pipeline timing (STT / LLM / TTS)."""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class RequestTiming:
    stt_ms: float | None = None
    llm_ms: float | None = None
    tts_ms: float | None = None
    extra: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        payload: dict[str, float] = {}
        if self.stt_ms is not None:
            payload["stt_ms"] = round(self.stt_ms, 2)
        if self.llm_ms is not None:
            payload["llm_ms"] = round(self.llm_ms, 2)
        if self.tts_ms is not None:
            payload["tts_ms"] = round(self.tts_ms, 2)
        for key, value in self.extra.items():
            payload[key] = round(value, 2)
        return payload


_timing_var: ContextVar[RequestTiming | None] = ContextVar("request_timing", default=None)


def get_request_timing() -> RequestTiming | None:
    return _timing_var.get()


def reset_request_timing() -> RequestTiming:
    timing = RequestTiming()
    _timing_var.set(timing)
    return timing


def clear_request_timing() -> None:
    _timing_var.set(None)


@contextmanager
def measure_phase(phase: str) -> Iterator[None]:
    """Record elapsed milliseconds for stt, llm, or tts on the active request."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        timing = _timing_var.get()
        if timing is None:
            return
        if phase == "stt":
            timing.stt_ms = (timing.stt_ms or 0) + elapsed_ms
        elif phase == "llm":
            timing.llm_ms = (timing.llm_ms or 0) + elapsed_ms
        elif phase == "tts":
            timing.tts_ms = (timing.tts_ms or 0) + elapsed_ms
        else:
            timing.extra[phase] = timing.extra.get(phase, 0) + elapsed_ms