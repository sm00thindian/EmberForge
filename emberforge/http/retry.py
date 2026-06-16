"""HTTP retry helpers with exponential backoff."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS_CODES


def _retry_delay(base_delay_seconds: float, attempt: int) -> float:
    return base_delay_seconds * (2**attempt)


async def post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
    **kwargs: Any,
) -> httpx.Response:
    """POST with retries on transient HTTP statuses and transport errors."""
    last_transport_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.post(url, **kwargs)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_transport_error = exc
            if attempt < max_retries:
                await asyncio.sleep(_retry_delay(base_delay_seconds, attempt))
                continue
            raise

        if is_retryable_status(response.status_code) and attempt < max_retries:
            await asyncio.sleep(_retry_delay(base_delay_seconds, attempt))
            continue

        return response

    if last_transport_error is not None:
        raise last_transport_error

    raise RuntimeError("post_with_retry exhausted without a response")