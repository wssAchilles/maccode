"""Common API response helpers."""

from __future__ import annotations

from typing import Any, Optional

from flask import jsonify


def success_response(
    data: Optional[Any] = None,
    *,
    meta: Optional[dict[str, Any]] = None,
    status_code: int = 200,
):
    payload = {
        'success': True,
        'data': data if data is not None else {},
        'meta': meta or {},
    }
    return jsonify(payload), status_code


def error_response(
    code: str,
    message: str,
    *,
    status_code: int = 400,
    details: Optional[Any] = None,
    meta: Optional[dict[str, Any]] = None,
):
    error = {
        'code': code,
        'message': message,
    }
    if details is not None:
        error['details'] = details

    payload = {
        'success': False,
        'error': error,
        'meta': meta or {},
    }
    return jsonify(payload), status_code
