from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from redis.asyncio import Redis


class RedisStrategyOrchestrationStateStore:
    def __init__(
        self,
        *,
        redis_getter: Callable[[], Redis | None],
        state_key: str,
    ) -> None:
        self._redis_getter = redis_getter
        self._state_key = state_key

    @property
    def backend_name(self) -> str:
        return "redis"

    async def load_state(self) -> dict[str, Any] | None:
        redis_client = self._redis_getter()
        if redis_client is None:
            return None
        raw = await redis_client.get(self._state_key)
        if not raw:
            return None
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
        return None

    async def save_state(self, state: dict[str, Any]) -> None:
        redis_client = self._redis_getter()
        if redis_client is None:
            return
        await redis_client.set(self._state_key, json.dumps(state, separators=(",", ":"), sort_keys=True))
