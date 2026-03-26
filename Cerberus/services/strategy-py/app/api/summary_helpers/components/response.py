from __future__ import annotations

from typing import Any


def component_ok(payload: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": status_code,
        "payload": payload,
    }


def component_error(
    *,
    code: str,
    message: str,
    request_id: str,
    status_code: int,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status_code": status_code,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        },
    }
