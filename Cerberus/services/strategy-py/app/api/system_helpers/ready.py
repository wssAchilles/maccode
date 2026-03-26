from __future__ import annotations

from time import monotonic
from typing import Any

from app.config import settings
from app.matching_observability import default_matching_health
from app.redis_worker import RedisMarketWorker

from .worker_state import build_worker_state


def _collect_stream_readiness_reasons(worker: RedisMarketWorker) -> list[str]:
    reasons: list[str] = []
    if not worker.redis_configured:
        reasons.append("redis_url_missing")
    if not worker.started:
        reasons.append("worker_not_started")
    if (
        settings.market_stream_enabled
        and not settings.market_stream_legacy_pubsub_fallback
        and worker.market_stream_fallbacks > 0
    ):
        reasons.append("market_stream_unstable")
    if (
        settings.market_stream_pending_warn_threshold > 0
        and worker.market_stream_pending > settings.market_stream_pending_warn_threshold
    ):
        reasons.append("market_stream_pending_high")
    if (
        settings.market_stream_lag_warn_threshold > 0
        and worker.market_stream_lag > settings.market_stream_lag_warn_threshold
    ):
        reasons.append("market_stream_lag_high")
    return reasons


async def _read_matching_ready(
    worker: RedisMarketWorker, request_id: str
) -> tuple[list[str], dict[str, Any]]:
    if not settings.matching_enabled:
        return [], default_matching_health(enabled=False)

    reasons: list[str] = []
    matching = await worker.matching_client.health(request_id=request_id)
    if not matching.get("reachable", False):
        reasons.append("matching_unreachable")
    if bool(matching.get("degraded", False)):
        reasons.append("matching_degraded")
    return reasons, matching


async def build_ready_content(
    worker: RedisMarketWorker,
    *,
    started_at: float,
    request_id: str,
) -> tuple[int, dict[str, Any]]:
    reasons = _collect_stream_readiness_reasons(worker)
    matching_reasons, matching = await _read_matching_ready(worker, request_id)
    reasons.extend(matching_reasons)

    status_code = 200 if not reasons else 503
    return status_code, {
        "ready": status_code == 200,
        "service": settings.service_name,
        "uptime_seconds": int(max(monotonic() - started_at, 0.0)),
        "reasons": reasons,
        "worker": build_worker_state(worker),
        "matching": matching,
        "request_id": request_id,
    }
