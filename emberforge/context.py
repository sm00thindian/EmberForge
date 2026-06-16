"""Per-request context propagated through the pipeline."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)


def ensure_request_id(request_id: str | None = None) -> str:
    resolved = request_id or get_request_id() or str(uuid.uuid4())
    set_request_id(resolved)
    return resolved