from __future__ import annotations

import asyncio
from typing import Any

from app.config import settings
from app.ports import (
    MatchingGatewayPort,
    PersistenceStatusPort,
    SignalHistorySource,
    SignalRuntimePort,
    SignalStorePort,
)


class SummaryApplicationService:
    def __init__(
        self,
        *,
        signal_runtime: SignalRuntimePort,
        signal_store: SignalStorePort,
        matching_gateway: MatchingGatewayPort,
        persistence_status: PersistenceStatusPort,
    ) -> None:
        self._signal_runtime = signal_runtime
        self._signal_store = signal_store
        self._matching_gateway = matching_gateway
        self._persistence_status = persistence_status

    async def summary(
        self,
        *,
        symbol: str,
        recent_limit: int,
        source: str,
        orderbook_depth: int,
        request_id: str,
    ) -> dict[str, Any]:
        normalized_symbol = _normalize_symbol(symbol)
        selected_source = _normalize_source(source)

        signal_component = self._build_signal_component()
        recent_component, persistence_component, orderbook_component = await asyncio.gather(
            self._build_recent_signals_component(
                limit=recent_limit,
                source=selected_source,
                request_id=request_id,
            ),
            self._build_persistence_component(request_id=request_id),
            self._build_matching_orderbook_component(
                symbol=normalized_symbol,
                depth=orderbook_depth,
                request_id=request_id,
            ),
        )

        return {
            "symbol": normalized_symbol,
            "source": selected_source,
            "recent_limit": recent_limit,
            "orderbook_depth": orderbook_depth,
            "signal": signal_component,
            "recent_signals": recent_component,
            "persistence": persistence_component,
            "matching_orderbook": orderbook_component,
        }

    def _build_signal_component(self) -> dict[str, Any]:
        signal = self._signal_runtime.read_current_signal()
        if signal is None:
            return _component_ok(
                {
                    "status": "warmup",
                    "signal": "HOLD",
                    "confidence": 0.0,
                }
            )
        return _component_ok(
            {
                "status": "ready",
                "signal": signal.signal,
                "confidence": signal.confidence,
                "symbol": signal.symbol,
            }
        )

    async def _build_recent_signals_component(
        self,
        *,
        limit: int,
        source: SignalHistorySource,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            used_source, records = await self._signal_store.list_recent(
                limit=limit,
                source=source,
            )
        except Exception as exc:
            return _component_error(
                code="summary_recent_signals_failed",
                message=f"recent signals unavailable: {exc}",
                request_id=request_id,
                status_code=502,
            )

        return _component_ok(
            {
                "source": used_source,
                "count": len(records),
                "signals": [item.model_dump() for item in records],
            }
        )

    async def _build_persistence_component(self, *, request_id: str) -> dict[str, Any]:
        try:
            payload = await self._persistence_status.get_persistence_status(
                request_id=request_id,
            )
        except Exception as exc:
            return _component_error(
                code="summary_persistence_failed",
                message=f"persistence status unavailable: {exc}",
                request_id=request_id,
                status_code=502,
            )
        return _component_ok(payload)

    async def _build_matching_orderbook_component(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            payload = await self._matching_gateway.get_order_book(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
            )
        except Exception as exc:
            return _component_ok(
                self._orderbook_degraded_payload(
                    symbol=symbol,
                    depth=depth,
                    request_id=request_id,
                    reason=_format_matching_error_reason(exc),
                )
            )

        if not payload.get("bids") and not payload.get("asks"):
            payload = {
                **payload,
                "degraded": payload.get("degraded", True),
                "reason": payload.get("reason") or "orderbook empty",
            }
        return _component_ok(payload)

    def _orderbook_degraded_payload(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "enabled": self._matching_gateway.enabled,
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


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return normalized or "BTCUSDT"


def _normalize_source(source: str) -> SignalHistorySource:
    if source == "supabase":
        return "supabase"
    if source == "firestore":
        return "firestore"
    return "auto"


def _component_ok(payload: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    return {
        "ok": True,
        "status_code": status_code,
        "payload": payload,
    }


def _component_error(
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


def _format_matching_error_reason(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    details = getattr(exc, "details", None)
    if callable(code) and callable(details):
        try:
            status_code = code()
            detail = details()
        except Exception:
            return str(exc)
        code_name = getattr(status_code, "name", None)
        if code_name and detail:
            return f"{code_name}: {detail}"
        if detail:
            return str(detail)
    return f"matching orderbook error: {exc}"

