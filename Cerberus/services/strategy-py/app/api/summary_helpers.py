from __future__ import annotations

from typing import Any, Literal

import grpc

from app.api.system_helpers import build_persistence_status
from app.config import settings
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore

SummarySource = Literal["auto", "supabase", "firestore"]


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return normalized or "BTCUSDT"


def normalize_source(source: str) -> SummarySource:
    if source == "supabase":
        return "supabase"
    if source == "firestore":
        return "firestore"
    return "auto"


def component_ok(payload: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": status_code,
        "payload": payload,
    }


def component_error(
    *,
    code: str,
    message: str,
    request_id: str,
    status_code: int,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status_code": status_code,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        },
    }


def build_signal_component(worker: RedisMarketWorker) -> dict[str, Any]:
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


async def build_recent_signals_component(
    signal_store: SignalStore,
    *,
    limit: int,
    source: SummarySource,
    request_id: str,
) -> dict[str, Any]:
    try:
        used_source, records = await signal_store.list_recent(limit=limit, source=source)
    except Exception as exc:
        return component_error(
            code="summary_recent_signals_failed",
            message=f"recent signals unavailable: {exc}",
            request_id=request_id,
            status_code=502,
        )

    return component_ok(
        {
            "source": used_source,
            "count": len(records),
            "signals": [item.model_dump() for item in records],
        }
    )


async def build_persistence_component(
    worker: RedisMarketWorker,
    signal_store: SignalStore,
    *,
    request_id: str,
) -> dict[str, Any]:
    try:
        payload = await build_persistence_status(worker, signal_store, request_id=request_id)
    except Exception as exc:
        return component_error(
            code="summary_persistence_failed",
            message=f"persistence status unavailable: {exc}",
            request_id=request_id,
            status_code=502,
        )
    return component_ok(payload)


def _orderbook_degraded_payload(
    *,
    symbol: str,
    depth: int,
    request_id: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "enabled": settings.matching_enabled,
        "degraded": True,
        "symbol": symbol,
        "depth": depth,
        "bids": [],
        "asks": [],
        "generated_at_ms": 0,
        "request_id": request_id,
        "reason": reason,
        "schema_version": settings.event_schema_version,
        "correlation_id": request_id,
    }


async def build_matching_orderbook_component(
    worker: RedisMarketWorker,
    *,
    symbol: str,
    depth: int,
    request_id: str,
) -> dict[str, Any]:
    try:
        payload = await worker.matching_client.get_order_book(
            symbol=symbol,
            depth=depth,
            request_id=request_id,
        )
    except grpc.aio.AioRpcError as exc:
        return component_ok(
            _orderbook_degraded_payload(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
                reason=f"{exc.code().name}: {exc.details()}",
            )
        )
    except Exception as exc:
        return component_ok(
            _orderbook_degraded_payload(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
                reason=f"matching orderbook error: {exc}",
            )
        )

    if not payload.get("bids") and not payload.get("asks"):
        payload = {
            **payload,
            "degraded": payload.get("degraded", True),
            "reason": payload.get("reason") or "orderbook empty",
        }
    return component_ok(payload)
