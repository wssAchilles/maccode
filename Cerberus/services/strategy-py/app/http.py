import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

REQUEST_ID_HEADER = "x-request-id"
IDEMPOTENCY_KEY_HEADER = "idempotency-key"
IDEMPOTENCY_KEY_ALT_HEADER = "x-idempotency-key"
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def sanitize_request_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed or len(trimmed) > 128:
        return None
    if all(ch.isalnum() or ch in "-_." for ch in trimmed):
        return trimmed
    return None


def request_id_from(request: Request) -> str:
    request_id = getattr(request.state, "request_id", "")
    if isinstance(request_id, str) and request_id:
        return request_id
    return "unknown"


def sanitize_idempotency_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed or len(trimmed) > 256:
        return None
    if all(ch.isalnum() or ch in "-_:.#" for ch in trimmed):
        return trimmed
    return None


def idempotency_key_from(request: Request) -> str | None:
    state_key = getattr(request.state, "idempotency_key", None)
    if isinstance(state_key, str) and state_key:
        return state_key

    return (
        sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_HEADER))
        or sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_ALT_HEADER))
    )


def error_response(
    request: Request, *, status_code: int, code: str, message: Any
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": str(message),
                "request_id": request_id_from(request),
            }
        },
    )


def _http_error_code_from_status(status_code: int) -> str:
    if status_code >= 500:
        return "internal_error"
    if status_code == 422:
        return "validation_error"
    if status_code >= 400:
        return "request_error"
    return "http_error"


def _extract_http_exception_detail(detail: Any, status_code: int) -> tuple[str, Any]:
    if isinstance(detail, dict):
        code = detail.get("code")
        message = detail.get("message", detail)
        normalized_code = (
            str(code).strip()
            if isinstance(code, str) and str(code).strip()
            else _http_error_code_from_status(status_code)
        )
        return normalized_code, message
    return _http_error_code_from_status(status_code), detail


def prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def register_error_handlers(app: FastAPI, logger: logging.Logger) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[override]
        code, detail = _extract_http_exception_detail(exc.detail, exc.status_code)
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):  # type: ignore[override]
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request, exc: Exception
    ):  # type: ignore[override]
        logger.exception("unhandled strategy error: %s", exc)
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="internal server error",
        )


def register_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[override]
        incoming = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
        idempotency_key = (
            sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_HEADER))
            or sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_ALT_HEADER))
        )
        request_id = incoming or uuid4().hex
        request.state.request_id = request_id
        request.state.idempotency_key = idempotency_key
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        if idempotency_key:
            response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
            response.headers[IDEMPOTENCY_KEY_ALT_HEADER] = idempotency_key
        return response
