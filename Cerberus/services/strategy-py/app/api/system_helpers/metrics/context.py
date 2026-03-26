from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.matching_observability import collect_matching_snapshot
from app.redis_worker import RedisMarketWorker


@dataclass(frozen=True)
class MatchingMetricsContext:
    status: str
    reachable: int
    degraded: int
    uptime_seconds: int
    stats: dict[str, Any]


async def build_matching_metrics_context(
    worker: RedisMarketWorker, *, request_id: str
) -> MatchingMetricsContext:
    snapshot = await collect_matching_snapshot(worker, request_id=request_id)
    health = snapshot.health
    return MatchingMetricsContext(
        status=str(health.get("status", "disabled")),
        reachable=1 if bool(health.get("reachable", False)) else 0,
        degraded=1 if bool(health.get("degraded", False)) else 0,
        uptime_seconds=int(health.get("uptime_seconds", 0)),
        stats=snapshot.stats,
    )


__all__ = ["MatchingMetricsContext", "build_matching_metrics_context"]
