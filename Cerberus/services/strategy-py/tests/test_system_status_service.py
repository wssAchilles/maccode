from __future__ import annotations

import pytest

from app.application import SystemStatusApplicationService
from app.config import settings
from app.matching_observability import MatchingSnapshot
from app.redis_worker.runtime_state import (
    MarketStreamRuntimeSnapshot,
    WorkerRuntimeSnapshot,
)
from app.schemas import MatchingHealthView, MatchingStatsView
from app.system_status_service import SystemStatusService
from app.system_status_query import PersistenceStatusResult, PersistenceStoresPayload


class FakeRuntimeStatus:
    def runtime_snapshot(self) -> WorkerRuntimeSnapshot:
        return WorkerRuntimeSnapshot(
            started=True,
            market_loop_running=True,
            execution_loop_running=False,
            redis_configured=True,
            tracked_symbols=("BTCUSDT", "ETHUSDT"),
            last_signal=None,
            processed_ticks=12,
            market_ingest_mode="stream",
            forwarded_executions=4,
            last_execution_id=77,
            last_tick_at="2026-03-27T12:00:00Z",
            last_tick_epoch_seconds=1_743_040_800,
            last_error="temporary warning",
            market_stream=MarketStreamRuntimeSnapshot(
                events=9,
                ack_failures=1,
                read_failures=2,
                retry_attempts=3,
                fallbacks=1,
                consecutive_failures=0,
                last_retry_backoff_ms=250,
                last_stream_id="123-0",
                pending=6,
                lag=8,
                reclaim_attempts=2,
                reclaimed=5,
                reclaim_failures=1,
                poisoned=1,
                last_reclaim_at_ms=1_743_040_800_000,
                last_poison_id="999-0",
            ),
        )

    def idempotency_snapshot(self) -> dict[str, object]:
        return {
            "redis_enabled": True,
            "signal_claim_attempts": 10,
            "signal_claim_conflicts": 1,
            "signal_claim_rollbacks": 0,
            "order_claim_attempts": 7,
            "order_claim_conflicts": 2,
            "order_claim_rollbacks": 1,
            "redis_errors": 0,
        }


class FakeStoreStatus:
    def status(self) -> PersistenceStoresPayload:
        return PersistenceStoresPayload(
            supabase_enabled=True,
            firebase_enabled=False,
            supabase_table="strategy_signals",
            firebase_collection="signals",
        )


class FakeMatchingObservability:
    def __init__(self, snapshot: MatchingSnapshot) -> None:
        self._snapshot = snapshot
        self.request_ids: list[str] = []

    @property
    def enabled(self) -> bool:
        return bool(self._snapshot.health.get("enabled", False))

    async def collect_snapshot(self, *, request_id: str) -> MatchingSnapshot:
        self.request_ids.append(request_id)
        return self._snapshot


def _build_service(
    snapshot: MatchingSnapshot,
) -> tuple[SystemStatusService, SystemStatusApplicationService, FakeMatchingObservability]:
    observability = FakeMatchingObservability(snapshot)
    application = SystemStatusApplicationService(
        runtime_status=FakeRuntimeStatus(),
        signal_store_status=FakeStoreStatus(),
        matching_observability=observability,
        started_at=0.0,
    )
    service = SystemStatusService(
        application=application,
    )
    return service, application, observability


@pytest.mark.asyncio
async def test_system_status_service_metrics_lines_use_observability_facade() -> None:
    service, _, observability = _build_service(
        MatchingSnapshot(
            health=MatchingHealthView(
                enabled=True,
                reachable=True,
                degraded=False,
                status="ok",
                service="matching-cpp",
                version="0.1.0",
                uptime_seconds=120,
            ),
            stats=MatchingStatsView(
                enabled=True,
                live_orders=0,
                trade_count=0,
                tracked_orders=0,
                rejected_orders=0,
                symbols=0,
                submit_order_latency_p95_ms=14.5,
                submit_order_throughput_rps=8.2,
                trade_throughput_rps=4.1,
                inflight_requests=2,
                inflight_requests_peak=5,
                max_inflight_requests=32,
                backpressure_waits_total=3,
                backpressure_rejections_total=1,
                backpressure_wait_timeouts_total=0,
                backpressure_wait_ms_total=45,
            ),
        )
    )

    lines = await service.metrics_lines(request_id="rid-metrics-facade")

    assert observability.request_ids == ["rid-metrics-facade"]
    assert "cerberus_strategy_matching_enabled 1" in lines
    assert 'cerberus_strategy_matching_status{status="ok"} 1' in lines
    assert "cerberus_strategy_processed_ticks_total 12" in lines


@pytest.mark.asyncio
async def test_system_status_service_ready_and_persistence_preserve_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "matching_enabled", True)
    service, application, observability = _build_service(
        MatchingSnapshot(
            health=MatchingHealthView(
                enabled=True,
                reachable=False,
                degraded=True,
                status="error",
                service="matching-cpp",
                version="0.1.0",
                uptime_seconds=0,
                reason="rpc timeout",
            ),
            stats=MatchingStatsView(
                enabled=True,
                live_orders=0,
                trade_count=0,
                tracked_orders=0,
                rejected_orders=0,
                symbols=0,
            ),
        )
    )

    status_code, ready_payload = await service.ready(request_id="rid-ready-facade")
    persistence_payload = await service.persistence(request_id="rid-persist-facade")
    typed_persistence = await application.persistence_status(
        request_id="rid-persist-typed-facade"
    )

    assert status_code == 503
    assert "matching_unreachable" in ready_payload["reasons"]
    assert "matching_degraded" in ready_payload["reasons"]
    assert ready_payload["matching"]["status"] == "error"

    assert observability.request_ids == [
        "rid-ready-facade",
        "rid-persist-facade",
        "rid-persist-typed-facade",
    ]
    assert isinstance(typed_persistence, PersistenceStatusResult)
    assert persistence_payload["status"] == "ok"
    assert persistence_payload["worker"]["processed_ticks"] == 12
    assert persistence_payload["worker"]["tracked_symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert persistence_payload["matching"]["health"]["reason"] == "rpc timeout"
    assert persistence_payload["stores"]["supabase_enabled"] is True
