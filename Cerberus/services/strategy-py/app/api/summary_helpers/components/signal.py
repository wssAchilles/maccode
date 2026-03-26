from __future__ import annotations

from app.redis_worker import RedisMarketWorker

from .response import component_ok


def build_signal_component(worker: RedisMarketWorker) -> dict[str, object]:
    if worker.last_signal is None:
        return component_ok(
            {
                "status": "warmup",
                "signal": "HOLD",
                "confidence": 0.0,
            }
        )
    return component_ok(
        {
            "status": "ready",
            "signal": worker.last_signal.signal,
            "confidence": worker.last_signal.confidence,
            "symbol": worker.last_signal.symbol,
        }
    )
