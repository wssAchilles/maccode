from __future__ import annotations

from typing import Any

import grpc


def metadata_to_dict(metadata: grpc.aio.Metadata | None) -> dict[str, str]:
    if metadata is None:
        return {}

    normalized: dict[str, str] = {}
    for key, value in metadata:
        key_text = str(key).strip().lower()
        if not key_text:
            continue
        if isinstance(value, bytes):
            value_text = value.decode("utf-8", errors="ignore").strip()
        else:
            value_text = str(value).strip()
        if value_text:
            normalized[key_text] = value_text
    return normalized


def degraded_hint(metadata: dict[str, str]) -> tuple[bool, str | None]:
    raw = metadata.get("x-cerberus-degraded", "")
    degraded = raw.lower() in {"1", "true", "yes", "on"}
    reason = metadata.get("x-cerberus-degraded-reason")
    return degraded, reason


async def await_unary_with_metadata(call: Any) -> tuple[Any, dict[str, str]]:
    response = await call
    trailing = await call.trailing_metadata()
    return response, metadata_to_dict(trailing)
