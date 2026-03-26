from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from app.config import settings


def cache_contains(cache: OrderedDict[str, float], key: str) -> bool:
    cleanup_expired(cache)
    return key in cache


def mark_processed(cache: OrderedDict[str, float], key: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    cache[key] = now
    cache.move_to_end(key)
    cleanup_expired(cache)
    while len(cache) > max(settings.idempotency_max_entries, 1):
        cache.popitem(last=False)


def cleanup_expired(cache: OrderedDict[str, float]) -> None:
    now = datetime.now(timezone.utc).timestamp()
    ttl = max(settings.signal_idempotency_ttl_seconds, 1)
    to_remove = [key for key, ts in cache.items() if now - ts > ttl]
    for key in to_remove:
        cache.pop(key, None)


__all__ = ["cache_contains", "mark_processed", "cleanup_expired"]
