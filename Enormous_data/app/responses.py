from __future__ import annotations

from typing import Any

from flask import g


def api_ok(data: Any = None, message: str = "ok", meta: dict[str, Any] | None = None):
    return {
        "code": 0,
        "message": message,
        "data": data if data is not None else {},
        "meta": {"request_id": getattr(g, "request_id", None), **(meta or {})},
    }


def api_error(message: str, status_code: int, code: int | None = None):
    return {
        "code": code or status_code,
        "message": message,
        "data": None,
        "meta": {"request_id": getattr(g, "request_id", None)},
    }, status_code
