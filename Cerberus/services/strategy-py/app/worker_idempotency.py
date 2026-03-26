from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class WorkerIdempotencyService:
    _IDEMPOTENCY_SCOPE_SIGNAL = "signal"
    _IDEMPOTENCY_SCOPE_ORDER = "order"

    def __init__(self, *, redis_getter: Callable[[], Redis | None]) -> None:
        self._redis_getter = redis_getter
        self._processed_signal_ids: OrderedDict[str, float] = OrderedDict()
        self._processed_order_ids: OrderedDict[str, float] = OrderedDict()
        self._signal_claim_attempts: int = 0
        self._signal_claim_conflicts: int = 0
        self._signal_claim_rollbacks: int = 0
        self._order_claim_attempts: int = 0
        self._order_claim_conflicts: int = 0
        self._order_claim_rollbacks: int = 0
        self._redis_errors: int = 0

    async def claim_signal(self, signal_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def release_signal(self, signal_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def claim_order(self, order_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    async def release_order(self, order_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    def snapshot(self) -> dict[str, int | bool]:
        return {
            "redis_enabled": self._redis_enabled(),
            "signal_claim_attempts": self._signal_claim_attempts,
            "signal_claim_conflicts": self._signal_claim_conflicts,
            "signal_claim_rollbacks": self._signal_claim_rollbacks,
            "order_claim_attempts": self._order_claim_attempts,
            "order_claim_conflicts": self._order_claim_conflicts,
            "order_claim_rollbacks": self._order_claim_rollbacks,
            "redis_errors": self._redis_errors,
        }

    async def _claim_idempotency_key(self, scope: str, key: str) -> bool:
        normalized = key.strip()
        if not normalized:
            return True

        self._increment_claim_attempt(scope)
        cache = self._cache_for_scope(scope)
        if self._cache_contains(cache, normalized):
            self._increment_claim_conflict(scope)
            return False

        redis_client = self._redis_getter()
        if redis_client is not None and settings.idempotency_store_redis_enabled:
            redis_key = self._redis_idempotency_key(scope, normalized)
            try:
                claimed = await redis_client.set(
                    redis_key,
                    "1",
                    nx=True,
                    ex=max(settings.signal_idempotency_ttl_seconds, 1),
                )
                if claimed:
                    self._mark_processed(cache, normalized)
                    return True
                self._mark_processed(cache, normalized)
                self._increment_claim_conflict(scope)
                return False
            except RedisError as exc:
                self._redis_errors += 1
                logger.warning(
                    "redis idempotency claim failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        return self._claim_with_local_cache(cache, normalized, scope)

    async def _release_idempotency_key(self, scope: str, key: str) -> None:
        normalized = key.strip()
        if not normalized:
            return

        redis_client = self._redis_getter()
        if redis_client is not None and settings.idempotency_store_redis_enabled:
            redis_key = self._redis_idempotency_key(scope, normalized)
            try:
                await redis_client.delete(redis_key)
            except RedisError as exc:
                self._redis_errors += 1
                logger.warning(
                    "redis idempotency release failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        self._cache_for_scope(scope).pop(normalized, None)
        self._increment_claim_rollback(scope)

    def _redis_enabled(self) -> bool:
        return self._redis_getter() is not None and settings.idempotency_store_redis_enabled

    def _redis_idempotency_key(self, scope: str, key: str) -> str:
        prefix = settings.idempotency_redis_key_prefix.strip() or "cerberus:idempotency"
        return f"{prefix}:{scope}:{key}"

    def _cache_for_scope(self, scope: str) -> OrderedDict[str, float]:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            return self._processed_order_ids
        return self._processed_signal_ids

    def _cache_contains(self, cache: OrderedDict[str, float], key: str) -> bool:
        self._cleanup_expired(cache)
        return key in cache

    def _claim_with_local_cache(
        self,
        cache: OrderedDict[str, float],
        key: str,
        scope: str,
    ) -> bool:
        if self._cache_contains(cache, key):
            self._increment_claim_conflict(scope)
            return False
        self._mark_processed(cache, key)
        return True

    def _increment_claim_attempt(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self._order_claim_attempts += 1
            return
        self._signal_claim_attempts += 1

    def _increment_claim_conflict(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self._order_claim_conflicts += 1
            return
        self._signal_claim_conflicts += 1

    def _increment_claim_rollback(self, scope: str) -> None:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            self._order_claim_rollbacks += 1
            return
        self._signal_claim_rollbacks += 1

    def _mark_processed(self, cache: OrderedDict[str, float], key: str) -> None:
        now = datetime.now(timezone.utc).timestamp()
        cache[key] = now
        cache.move_to_end(key)
        self._cleanup_expired(cache)
        while len(cache) > max(settings.idempotency_max_entries, 1):
            cache.popitem(last=False)

    def _cleanup_expired(self, cache: OrderedDict[str, float]) -> None:
        now = datetime.now(timezone.utc).timestamp()
        ttl = max(settings.signal_idempotency_ttl_seconds, 1)
        to_remove = [key for key, ts in cache.items() if now - ts > ttl]
        for key in to_remove:
            cache.pop(key, None)
