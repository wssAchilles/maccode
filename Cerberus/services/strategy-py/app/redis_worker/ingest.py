from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.event_runtime import publish_signal_and_matching_submission

if TYPE_CHECKING:
    from app.redis_worker.service import RedisMarketWorker
    from app.schemas import Signal, TickEvent


async def ingest_tick(worker: RedisMarketWorker, tick: TickEvent) -> Signal:
    signal, signal_id = worker._signal_engine.evaluate_tick(tick)
    if not await worker.claim_signal(signal_id):
        return signal

    try:
        worker.last_signal = signal

        if worker._redis is not None:
            await publish_signal_and_matching_submission(worker, signal, tick, signal_id)

        await worker._firebase.publish_signal(signal)
        await worker._supabase.publish_signal(signal)
    except Exception:
        await worker.release_signal_claim(signal_id)
        raise

    record_tick_processed(worker)
    return signal


def record_tick_processed(worker: RedisMarketWorker) -> None:
    worker.processed_ticks += 1
    now = datetime.now(timezone.utc)
    worker.last_tick_at = now.isoformat()
    worker.last_tick_epoch_seconds = int(now.timestamp())
    worker.last_error = None
