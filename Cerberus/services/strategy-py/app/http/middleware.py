from fastapi import FastAPI, Request

from .constants import (
    IDEMPOTENCY_KEY_ALT_HEADER,
    IDEMPOTENCY_KEY_HEADER,
    REQUEST_ID_HEADER,
)
from .request_ids import build_request_context_headers


def register_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[override]
        request_id, idempotency_key = build_request_context_headers(request)
        request.state.request_id = request_id
        request.state.idempotency_key = idempotency_key
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        if idempotency_key:
            response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
            response.headers[IDEMPOTENCY_KEY_ALT_HEADER] = idempotency_key
        return response
