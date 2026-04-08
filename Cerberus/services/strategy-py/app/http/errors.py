import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .request_ids import request_id_from


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: Any,
    details: Any | None = None,
) -> JSONResponse:
    error = {
        "code": code,
        "message": message if isinstance(message, str) else str(message),
        "request_id": request_id_from(request),
    }
    if details is not None:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error
        },
    )


def register_error_handlers(app: FastAPI, logger: logging.Logger) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[override]
        code, detail, details = extract_http_exception_detail(exc.detail, exc.status_code)
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=detail,
            details=details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):  # type: ignore[override]
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="validation failed",
            details=exc.errors(),
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


def extract_http_exception_detail(
    detail: Any, status_code: int
) -> tuple[str, Any, Any | None]:
    if isinstance(detail, dict):
        code = detail.get("code")
        message = detail.get("message", detail)
        details = detail.get("details")
        normalized_code = (
            str(code).strip()
            if isinstance(code, str) and str(code).strip()
            else http_error_code_from_status(status_code)
        )
        return normalized_code, message, details
    return http_error_code_from_status(status_code), detail, None


def http_error_code_from_status(status_code: int) -> str:
    if status_code >= 500:
        return "internal_error"
    if status_code == 422:
        return "validation_error"
    if status_code >= 400:
        return "request_error"
    return "http_error"
