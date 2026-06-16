"""Global API exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from emberforge.context import ensure_request_id, get_request_id
from emberforge.errors import EmberForgeError


def _error_body(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    request_id: str | None = None,
) -> dict:
    rid = ensure_request_id(request_id or get_request_id())
    return {
        "code": code,
        "message": message,
        "retryable": retryable,
        "request_id": rid,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmberForgeError)
    async def handle_emberforge_error(_request: Request, exc: EmberForgeError) -> JSONResponse:
        rid = ensure_request_id(exc.request_id or get_request_id())
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(rid),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = ensure_request_id(get_request_id())
        message = "Request validation failed"
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(part) for part in first.get("loc", ()))
            detail = first.get("msg", "")
            if loc:
                message = f"{loc}: {detail}"
            elif detail:
                message = detail

        return JSONResponse(
            status_code=422,
            content=_error_body("VALIDATION_ERROR", message, request_id=rid),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        rid = ensure_request_id(get_request_id())
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message") or str(detail)
        else:
            message = str(detail)

        code = "UNAUTHORIZED" if exc.status_code == 401 else "HTTP_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, message, request_id=rid),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        rid = ensure_request_id(get_request_id())
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                request_id=rid,
            ),
            headers={"X-Request-ID": rid},
        )