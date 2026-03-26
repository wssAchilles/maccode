from __future__ import annotations

from typing import Any


def normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def response_context(response: Any, fallback_request_id: str) -> tuple[str | None, str]:
    schema_version = normalize_text(getattr(response, "schema_version", None))
    correlation_id = normalize_text(getattr(response, "correlation_id", None))
    return schema_version, correlation_id or fallback_request_id


__all__ = ["normalize_text", "response_context"]
