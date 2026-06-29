"""HTTP middleware."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from emberforge.context import get_request_id, set_request_id
from emberforge.observability.timing import get_request_timing, reset_request_timing
from emberforge.errors import rate_limited
from emberforge.security.rate_limit import get_rate_limiter, rate_limit_key
from emberforge.security.redaction import SecretRedactionFilter
from emberforge.security.request_context import client_ip
from emberforge.settings import get_settings

_RATE_LIMIT_SKIP_PREFIXES = ("/health", "/version")


def _path_limit(path: str, settings) -> int:
    if "/converse" in path:
        return settings.rate_limit_converse_per_minute
    return settings.rate_limit_default_per_minute


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate X-Request-ID through the request lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Log request duration and pipeline phase timings (STT / LLM / TTS)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        reset_request_timing()
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        timing = get_request_timing()
        timing_payload = timing.to_dict() if timing else {}

        logger = logging.getLogger("emberforge.http")
        timing_suffix = ""
        if timing_payload and "/converse" in request.url.path:
            timing_suffix = " " + " ".join(
                f"{key.replace('_ms', '')}={value}ms" for key, value in sorted(timing_payload.items())
            )

        logger.info(
            "%s %s %s %.2fms%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            timing_suffix,
            extra={
                "event": "http_request",
                "request_id": get_request_id(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "timing": timing_payload,
            },
        )
        if timing_payload:
            response.headers["X-Timing-Total-Ms"] = str(duration_ms)
            for key, value in timing_payload.items():
                response.headers[f"X-Timing-{key.replace('_ms', '').title()}-Ms"] = str(value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP / per-device sliding-window rate limits."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.rate_limits_active:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in _RATE_LIMIT_SKIP_PREFIXES):
            return await call_next(request)

        device_id = request.headers.get("X-Device-ID")
        key = rate_limit_key(path, client_ip(request), device_id=device_id)
        limit = _path_limit(path, settings)
        if not get_rate_limiter().allow(key, limit=limit):
            rid = get_request_id()
            error = rate_limited(request_id=rid)
            return JSONResponse(
                status_code=error.status_code,
                content=error.to_dict(rid),
                headers={"X-Request-ID": rid or ""},
            )

        return await call_next(request)


def configure_security_logging() -> None:
    """Attach secret redaction to root logging (idempotent)."""
    root = logging.getLogger()
    for existing in root.filters:
        if isinstance(existing, SecretRedactionFilter):
            return
    root.addFilter(SecretRedactionFilter())