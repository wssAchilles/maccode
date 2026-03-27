from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any

from app.config import settings
from app.matching_observability import default_matching_health
from app.ports import MatchingObservabilityPort, RuntimeStatusPort
from app.schemas import MatchingHealthView

from .worker_state import build_worker_state


@dataclass(frozen=True, slots=True)
class ReadyPayload:
    ready: bool
    service: str
    uptime_seconds: int
    reasons: list[str]
    worker: dict[str, Any]
    matching: MatchingHealthView
    request_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "service": self.service,
            "uptime_seconds": self.uptime_seconds,
            "reasons": self.reasons,
            "worker": self.worker,
            "matching": self.matching.model_dump(),
            "request_id": self.request_id,
        }


def _collect_stream_readiness_reasons(runtime_status: RuntimeStatusPort) -> list[str]:
    snapshot = runtime_status.runtime_snapshot()
    reasons: list[str] = []
    if not snapshot.redis_configured:
        reasons.append("redis_url_missing")
    if not snapshot.started:
        reasons.append("worker_not_started")
    if (
        settings.market_stream_enabled
        and not settings.market_stream_legacy_pubsub_fallback
        and snapshot.market_stream.fallbacks > 0
    ):
        reasons.append("market_stream_unstable")
    if (
        settings.market_stream_pending_warn_threshold > 0
        and snapshot.market_stream.pending > settings.market_stream_pending_warn_threshold
    ):
        reasons.append("market_stream_pending_high")
    if (
        settings.market_stream_lag_warn_threshold > 0
        and snapshot.market_stream.lag > settings.market_stream_lag_warn_threshold
    ):
        reasons.append("market_stream_lag_high")
    return reasons


async def _read_matching_ready(
    matching_observability: MatchingObservabilityPort,
    request_id: str,
) -> tuple[list[str], MatchingHealthView]:
    if not settings.matching_enabled:
        return [], default_matching_health(enabled=False)

    reasons: list[str] = []
    matching = (await matching_observability.collect_snapshot(request_id=request_id)).health
    if not matching.reachable:
        reasons.append("matching_unreachable")
    if matching.degraded:
        reasons.append("matching_degraded")
    return reasons, matching


async def build_ready_content(
    runtime_status: RuntimeStatusPort,
    matching_observability: MatchingObservabilityPort,
    *,
    started_at: float,
    request_id: str,
) -> tuple[int, ReadyPayload]:
    reasons = _collect_stream_readiness_reasons(runtime_status)
    matching_reasons, matching = await _read_matching_ready(
        matching_observability,
        request_id,
    )
    reasons.extend(matching_reasons)

    status_code = 200 if not reasons else 503
    return status_code, ReadyPayload(
        ready=status_code == 200,
        service=settings.service_name,
        uptime_seconds=int(max(monotonic() - started_at, 0.0)),
        reasons=reasons,
        worker=build_worker_state(runtime_status),
        matching=matching,
        request_id=request_id,
    )
