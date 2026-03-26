from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

from .cache import cache_contains, mark_processed
from .counters import IdempotencyCounters

logger = logging.getLogger(__name__)


class WorkerIdempotencyService:
    _IDEMPOTENCY_SCOPE_SIGNAL = "signal"
    _IDEMPOTENCY_SCOPE_ORDER = "order"

    def __init__(self, *, redis_getter: Callable[[], Redis | None]) -> None:
        self._redis_getter = redis_getter
        self._processed_signal_ids: OrderedDict[str, float] = OrderedDict()
        self._processed_order_ids: OrderedDict[str, float] = OrderedDict()
        self._counters = IdempotencyCounters()

    async def claim_signal(self, signal_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def release_signal(self, signal_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_SIGNAL, signal_id)

    async def claim_order(self, order_id: str) -> bool:
        return await self._claim_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    async def release_order(self, order_id: str) -> None:
        await self._release_idempotency_key(self._IDEMPOTENCY_SCOPE_ORDER, order_id)

    def snapshot(self) -> dict[str, int | bool]:
        return self._counters.snapshot(redis_enabled=self._redis_enabled())

    async def _claim_idempotency_key(self, scope: str, key: str) -> bool:
        normalized = key.strip()
        if not normalized:
            return True

        order_scope = scope == self._IDEMPOTENCY_SCOPE_ORDER
        self._counters.increment_claim_attempt(order_scope=order_scope)
        cache = self._cache_for_scope(scope)
        if cache_contains(cache, normalized):
            self._counters.increment_claim_conflict(order_scope=order_scope)
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
                    mark_processed(cache, normalized)
                    return True
                mark_processed(cache, normalized)
                self._counters.increment_claim_conflict(order_scope=order_scope)
                return False
            except RedisError as exc:
                self._counters.increment_redis_error()
                logger.warning(
                    "redis idempotency claim failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        return self._claim_with_local_cache(cache, normalized, order_scope=order_scope)

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
                self._counters.increment_redis_error()
                logger.warning(
                    "redis idempotency release failed (scope=%s, key=%s): %s",
                    scope,
                    normalized,
                    exc,
                )

        self._cache_for_scope(scope).pop(normalized, None)
        self._counters.increment_claim_rollback(
            order_scope=scope == self._IDEMPOTENCY_SCOPE_ORDER
        )

    def _redis_enabled(self) -> bool:
        return self._redis_getter() is not None and settings.idempotency_store_redis_enabled

    def _redis_idempotency_key(self, scope: str, key: str) -> str:
        prefix = settings.idempotency_redis_key_prefix.strip() or "cerberus:idempotency"
        return f"{prefix}:{scope}:{key}"

    def _cache_for_scope(self, scope: str) -> OrderedDict[str, float]:
        if scope == self._IDEMPOTENCY_SCOPE_ORDER:
            return self._processed_order_ids
        return self._processed_signal_ids

    def _claim_with_local_cache(
        self,
        cache: OrderedDict[str, float],
        key: str,
        *,
        order_scope: bool,
    ) -> bool:
        if cache_contains(cache, key):
            self._counters.increment_claim_conflict(order_scope=order_scope)
            return False
        mark_processed(cache, key)
        return True


__all__ = ["WorkerIdempotencyService"]
