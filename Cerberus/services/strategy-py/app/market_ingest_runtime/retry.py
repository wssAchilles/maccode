from __future__ import annotations

import asyncio

import grpc
from redis.exceptions import RedisError

from app.config import settings


def is_retriable_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, ConnectionError, RedisError)):
        return True
    if isinstance(exc, grpc.aio.AioRpcError):
        return exc.code() in {
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            grpc.StatusCode.ABORTED,
        }
    return False


def compute_backoff_seconds(attempt: int) -> float:
    base = max(settings.retriable_base_backoff_seconds, 0.01)
    maximum = max(settings.retriable_max_backoff_seconds, base)
    value = base * (2 ** max(attempt - 1, 0))
    return min(value, maximum)


def compute_market_stream_backoff_ms(attempt: int) -> int:
    base = max(settings.market_stream_retry_backoff_ms, 1)
    maximum = max(settings.market_stream_retry_backoff_max_ms, base)
    value = base * (2 ** max(attempt - 1, 0))
    return min(value, maximum)
