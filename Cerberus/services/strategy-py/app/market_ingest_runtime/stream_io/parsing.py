from __future__ import annotations

from typing import Any


def flatten_stream_entries(raw: Any) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(raw, list):
        return entries
    for stream_bucket in raw:
        if not isinstance(stream_bucket, (list, tuple)) or len(stream_bucket) != 2:
            continue
        bucket_entries = stream_bucket[1]
        if not isinstance(bucket_entries, list):
            continue
        for item in bucket_entries:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            stream_id, fields = item
            if not isinstance(stream_id, str) or not isinstance(fields, dict):
                continue
            entries.append((stream_id, fields))
    return entries


def flatten_claimed_entries(raw: Any) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        claimed = raw[1]
    else:
        claimed = []

    entries: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(claimed, list):
        return entries

    for item in claimed:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        stream_id, fields = item
        if isinstance(stream_id, bytes):
            stream_id = stream_id.decode("utf-8", errors="ignore")
        if not isinstance(stream_id, str) or not isinstance(fields, dict):
            continue
        entries.append((stream_id, normalize_stream_fields(fields)))
    return entries


def normalize_stream_fields(fields: dict[Any, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(key, bytes):
            normalized_key = key.decode("utf-8", errors="ignore")
        else:
            normalized_key = str(key)
        normalized[normalized_key] = value
    return normalized


def parse_pending_range_entry(item: Any) -> dict[str, int]:
    if not isinstance(item, dict):
        return {"times_delivered": 1}
    times_delivered = item.get("times_delivered")
    if times_delivered is None:
        times_delivered = item.get(b"times_delivered")
    if times_delivered is None:
        times_delivered = 1
    if isinstance(times_delivered, int):
        return {"times_delivered": times_delivered}
    if isinstance(times_delivered, str) and times_delivered.isdigit():
        return {"times_delivered": int(times_delivered)}
    if isinstance(times_delivered, bytes):
        decoded = times_delivered.decode("utf-8", errors="ignore")
        if decoded.isdigit():
            return {"times_delivered": int(decoded)}
    return {"times_delivered": 1}


def extract_market_pending_count(raw: Any) -> int:
    if isinstance(raw, dict):
        value = raw.get("pending", 0)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0
    if isinstance(raw, (list, tuple)) and raw:
        first = raw[0]
        if isinstance(first, int):
            return max(first, 0)
        if isinstance(first, str) and first.isdigit():
            return int(first)
    return 0


def extract_market_lag(raw: Any, group: str) -> int:
    if not isinstance(raw, list):
        return 0

    target = group.strip()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="ignore")
        if not isinstance(name, str) or name.strip() != target:
            continue

        lag_value = item.get("lag", 0)
        if isinstance(lag_value, int):
            return max(lag_value, 0)
        if isinstance(lag_value, str) and lag_value.isdigit():
            return int(lag_value)
        return 0

    return 0
