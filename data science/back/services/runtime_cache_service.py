"""Small in-memory TTL cache for high-frequency read endpoints."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Tuple


class RuntimeCacheService:
    _lock = threading.Lock()
    _cache: Dict[str, Tuple[float, Any]] = {}

    @classmethod
    def get_or_set(
        cls,
        key: str,
        builder: Callable[[], Any],
        *,
        ttl_s: float,
    ) -> Any:
        now = time.time()
        with cls._lock:
            cached = cls._cache.get(key)
            if cached is not None:
                expires_at, value = cached
                if expires_at > now:
                    return value

        value = builder()
        with cls._lock:
            cls._cache[key] = (now + max(ttl_s, 0.0), value)
        return value

    @classmethod
    def invalidate_prefix(cls, prefix: str) -> None:
        with cls._lock:
            stale_keys = [key for key in cls._cache if key.startswith(prefix)]
            for key in stale_keys:
                cls._cache.pop(key, None)
