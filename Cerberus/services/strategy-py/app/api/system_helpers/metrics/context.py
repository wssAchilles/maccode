from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ports import MatchingObservabilityPort


@dataclass(frozen=True)
class MatchingMetricsContext:
    enabled: int
    status: str
    reachable: int
    degraded: int
    uptime_seconds: int
    stats: dict[str, Any]


async def build_matching_metrics_context(
    matching_observability: MatchingObservabilityPort,
    *,
    request_id: str,
) -> MatchingMetricsContext:
    snapshot = await matching_observability.collect_snapshot(request_id=request_id)
    health = snapshot.health
    return MatchingMetricsContext(
        enabled=1 if bool(health.get("enabled", False)) else 0,
        status=str(health.get("status", "disabled")),
        reachable=1 if bool(health.get("reachable", False)) else 0,
        degraded=1 if bool(health.get("degraded", False)) else 0,
        uptime_seconds=int(health.get("uptime_seconds", 0)),
        stats=snapshot.stats,
    )


__all__ = ["MatchingMetricsContext", "build_matching_metrics_context"]
