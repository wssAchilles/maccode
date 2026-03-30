from __future__ import annotations

import asyncio

from app.application.inference import InferenceApplicationService
from app.config import settings
from app.ports import (
    MatchingGatewayPort,
    PersistenceStatusPort,
    SignalHistorySource,
    SignalRuntimePort,
    SignalStorePort,
)
from app.schemas import MatchingOrderBookView
from app.summary_query import (
    SummaryComponent,
    SummaryRecentSignalsPayload,
    SummaryResult,
    SummarySignalPayload,
)


class SummaryApplicationService:
    def __init__(
        self,
        *,
        inference_application: InferenceApplicationService,
        signal_runtime: SignalRuntimePort,
        signal_store: SignalStorePort,
        matching_gateway: MatchingGatewayPort,
        persistence_status: PersistenceStatusPort,
    ) -> None:
        self._inference_application = inference_application
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
    ) -> SummaryResult:
        normalized_symbol = _normalize_symbol(symbol)
        selected_source = _normalize_source(source)

        signal_component = self._build_signal_component()
        recent_component, persistence_component, orderbook_component, inference_component = await asyncio.gather(
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
            self._build_inference_status_component(request_id=request_id),
        )

        return SummaryResult(
            symbol=normalized_symbol,
            source=selected_source,
            recent_limit=recent_limit,
            orderbook_depth=orderbook_depth,
            signal=signal_component,
            recent_signals=recent_component,
            persistence=persistence_component,
            matching_orderbook=orderbook_component,
            inference_status=inference_component,
        )

    def _build_signal_component(self) -> SummaryComponent:
        decision = self._signal_runtime.read_current_decision()
        if decision is not None:
            return SummaryComponent.ok_result(
                SummarySignalPayload(
                    status="ready",
                    signal=decision.signal.signal,
                    confidence=decision.signal.confidence,
                    symbol=decision.signal.symbol,
                    strategy_id=decision.signal.strategy_id,
                    engine=decision.engine,
                    decision_source=decision.decision_source,
                    dispatch_state=decision.dispatch_state,
                    inference_mode=decision.inference_mode,
                    signal_id=decision.signal_id,
                    strategy_basket=decision.strategies,
                    portfolio=decision.portfolio,
                )
            )

        signal = self._signal_runtime.read_current_signal()
        if signal is None:
            return SummaryComponent.ok_result(
                SummarySignalPayload(
                    status="warmup",
                    signal="HOLD",
                    confidence=0.0,
                )
            )
        return SummaryComponent.ok_result(
            SummarySignalPayload(
                status="ready",
                signal=signal.signal,
                confidence=signal.confidence,
                symbol=signal.symbol,
                strategy_id=signal.strategy_id,
            )
        )

    async def _build_recent_signals_component(
        self,
        *,
        limit: int,
        source: SignalHistorySource,
        request_id: str,
    ) -> SummaryComponent:
        try:
            used_source, records = await self._signal_store.list_recent(
                limit=limit,
                source=source,
            )
        except Exception as exc:
            return SummaryComponent.error_result(
                code="summary_recent_signals_failed",
                message=f"recent signals unavailable: {exc}",
                request_id=request_id,
                status_code=502,
            )

        return SummaryComponent.ok_result(
            SummaryRecentSignalsPayload(
                source=used_source,
                count=len(records),
                signals=records,
            )
        )

    async def _build_persistence_component(self, *, request_id: str) -> SummaryComponent:
        try:
            payload = await self._persistence_status.get_persistence_status(
                request_id=request_id,
            )
        except Exception as exc:
            return SummaryComponent.error_result(
                code="summary_persistence_failed",
                message=f"persistence status unavailable: {exc}",
                request_id=request_id,
                status_code=502,
            )
        return SummaryComponent.ok_result(payload)

    async def _build_matching_orderbook_component(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
    ) -> SummaryComponent:
        try:
            payload = await self._matching_gateway.get_order_book(
                symbol=symbol,
                depth=depth,
                request_id=request_id,
            )
        except Exception as exc:
            return SummaryComponent.ok_result(
                self._degraded_orderbook(
                    symbol=symbol,
                    depth=depth,
                    request_id=request_id,
                    reason=_format_matching_error_reason(exc),
                )
            )

        if not payload.bids and not payload.asks:
            payload = payload.model_copy(
                update={
                    "degraded": payload.degraded or True,
                    "reason": payload.reason or "orderbook empty",
                }
            )
        return SummaryComponent.ok_result(payload)

    def _degraded_orderbook(
        self,
        *,
        symbol: str,
        depth: int,
        request_id: str,
        reason: str,
    ) -> MatchingOrderBookView:
        return MatchingOrderBookView.model_validate(
            {
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
        )

    async def _build_inference_status_component(self, *, request_id: str) -> SummaryComponent:
        try:
            payload = (await self._inference_application.status()).to_dict()
        except Exception as exc:
            return SummaryComponent.error_result(
                code="summary_inference_status_failed",
                message=f"inference status unavailable: {exc}",
                request_id=request_id,
                status_code=502,
            )
        return SummaryComponent.ok_result(payload)


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return normalized or "BTCUSDT"


def _normalize_source(source: str) -> SignalHistorySource:
    if source == "supabase":
        return "supabase"
    if source == "firestore":
        return "firestore"
    return "auto"


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
