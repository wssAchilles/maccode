from __future__ import annotations

from app.api.system_helpers.metrics.line_builders.worker import (
    market_stream_metrics_lines,
    worker_runtime_metrics_lines,
)
from app.api.system_helpers.worker_state import build_worker_state
from app.redis_worker.runtime_state import (
    MarketStreamRuntimeSnapshot,
    WorkerRuntimeSnapshot,
)


class FakeWorker:
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


def test_build_worker_state_reads_runtime_snapshot() -> None:
    payload = build_worker_state(FakeWorker())  # type: ignore[arg-type]

    assert payload["started"] is True
    assert payload["market_ingest_mode"] == "stream"
    assert payload["market_stream_events"] == 9
    assert payload["market_stream_pending"] == 6
    assert payload["last_market_stream_poison_id"] == "999-0"


def test_worker_runtime_metrics_lines_emit_snapshot_values() -> None:
    worker = FakeWorker()

    runtime_lines = worker_runtime_metrics_lines(worker)  # type: ignore[arg-type]
    stream_lines = market_stream_metrics_lines(worker)  # type: ignore[arg-type]

    assert 'cerberus_strategy_market_ingest_mode{mode="stream"} 1' in runtime_lines
    assert "cerberus_strategy_processed_ticks_total 12" in runtime_lines
    assert "cerberus_strategy_tracked_symbols 2" in runtime_lines
    assert "cerberus_strategy_last_error 1" in runtime_lines
    assert "cerberus_strategy_market_stream_events_total 9" in stream_lines
    assert "cerberus_strategy_market_stream_last_retry_backoff_ms 250" in stream_lines
