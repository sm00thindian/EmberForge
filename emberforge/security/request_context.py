"""Request trust helpers."""

from __future__ import annotations

from starlette.requests import Request

_TRUSTED_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def is_trusted_local(request: Request) -> bool:
    host = client_ip(request)
    return host in _TRUSTED_HOSTS