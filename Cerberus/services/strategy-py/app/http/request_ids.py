from uuid import uuid4

from fastapi import Request

from .constants import (
    IDEMPOTENCY_KEY_ALT_HEADER,
    IDEMPOTENCY_KEY_HEADER,
    REQUEST_ID_HEADER,
)


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


def build_request_context_headers(request: Request) -> tuple[str, str | None]:
    incoming = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
    idempotency_key = (
        sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_HEADER))
        or sanitize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_ALT_HEADER))
    )
    request_id = incoming or uuid4().hex
    return request_id, idempotency_key


def prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
