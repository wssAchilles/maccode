from __future__ import annotations

import pytest

from app.application import InferenceStatusResult, SummaryApplicationService
from app.ports import (
    InferenceComparisonSnapshot,
    InferenceEngineStatus,
    InferenceRolloutSnapshot,
    PortfolioSignalSnapshot,
    RegisteredModel,
    SignalDecisionSnapshot,
    StrategyDecisionSnapshot,
    StrategyRegistryEntrySnapshot,
    StrategyRegistrySnapshot,
)
from app.schemas import (
    MatchingHealthView,
    MatchingOrderBookView,
    MatchingStatsView,
    Signal,
    SignalRecord,
)
from app.system_status_query import (
    PersistenceMatchingPayload,
    PersistenceStatusResult,
    PersistenceStoresPayload,
    PersistenceWorkerPayload,
)
from app.summary_query import SummaryRecentSignalsPayload, SummaryResult, SummarySignalPayload


class FakeSignalRuntime:
    def read_current_signal(self) -> Signal | None:
        return Signal(
            strategy_id="default",
            symbol="BTCUSDT",
            signal="BUY",
            confidence=0.91,
        )

    def read_current_decision(self) -> SignalDecisionSnapshot | None:
        signal = self.read_current_signal()
        assert signal is not None
        return SignalDecisionSnapshot(
            signal=signal,
            engine="moving_average",
            signal_id="sig-typed-001",
            dispatch_state="accepted",
            decision_source="rule_engine",
            inference_mode="observe",
            strategies=(
                StrategyDecisionSnapshot(
                    strategy_id="default",
                    label="Rule engine",
                    engine="moving_average",
                    signal="BUY",
                    confidence=0.91,
                    weight=0.62,
                    priority=1,
                    role="baseline",
                    active=True,
                    source="rule_engine",
                ),
                StrategyDecisionSnapshot(
                    strategy_id="inference",
                    label="Inference model",
                    engine="cerberus_signal_transformer_lstm",
                    signal="SELL",
                    confidence=0.64,
                    weight=0.38,
                    priority=2,
                    role="adaptive",
                    active=False,
                    source="inference",
                    reason="running in observe",
                    metadata={"model_id": "cerberus-transformer-lstm", "model_version": "v1"},
                ),
            ),
            portfolio=PortfolioSignalSnapshot(
                symbol="BTCUSDT",
                dominant_signal="BUY",
                final_signal="BUY",
                final_source="rule_engine",
                signal_bias="bullish",
                consensus_level="moderate",
                execution_ready=False,
                execution_gate="review",
                execution_gate_reason="strategy basket is still contested",
                lead_strategy_id="default",
                lead_strategy_label="Rule engine",
                aligned_count=1,
                contested_count=1,
                agreement_ratio=0.5,
                weighted_score=0.5642,
                active_strategy_count=2,
                tracked_symbols=("BTCUSDT", "ETHUSDT"),
                updated_at="2026-03-30T10:00:00Z",
                latest_price=101.25,
            ),
            registry=StrategyRegistrySnapshot(
                symbol="BTCUSDT",
                tracked_symbols=("BTCUSDT", "ETHUSDT"),
                conflict_policy="review_on_conflict",
                downgrade_policy="review",
                entries=(
                    StrategyRegistryEntrySnapshot(
                        strategy_id="default",
                        label="Rule engine",
                        engine="moving_average",
                        source="rule_engine",
                        role="baseline",
                        enabled=True,
                        priority=1,
                        configured_weight=0.62,
                        effective_weight=0.62,
                        symbol_coverage=("BTCUSDT", "ETHUSDT"),
                    ),
                    StrategyRegistryEntrySnapshot(
                        strategy_id="inference",
                        label="Inference model",
                        engine="cerberus_signal_transformer_lstm",
                        source="inference",
                        role="adaptive",
                        enabled=True,
                        priority=2,
                        configured_weight=0.38,
                        effective_weight=0.38,
                        symbol_coverage=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
                        metadata={"model_id": "cerberus-transformer-lstm"},
                    ),
                ),
            ),
            metadata={},
        )

    def store_current_decision(self, decision) -> None:
        del decision

    def tracked_symbols(self) -> tuple[str, ...]:
        return ("BTCUSDT", "ETHUSDT")


class FakeSignalStore:
    async def list_recent(
        self,
        limit: int,
        source: str = "auto",
    ) -> tuple[str, list[SignalRecord]]:
        assert limit == 2
        assert source == "supabase"
        return (
            "supabase",
            [
                SignalRecord(
                    strategy_id="default",
                    symbol="BTCUSDT",
                    signal="BUY",
                    confidence=0.82,
                    created_at="2026-03-27T10:00:00Z",
                )
            ],
        )


class FakeMatchingGateway:
    enabled = True

    async def get_order_book(
        self,
        *,
        symbol: str,
        depth: int = 20,
        request_id: str | None = None,
    ) -> MatchingOrderBookView:
        assert symbol == "BTCUSDT"
        assert depth == 5
        assert request_id == "rid-summary-typed-001"
        return MatchingOrderBookView(
            enabled=True,
            symbol=symbol,
            depth=depth,
            bids=[{"price": 100.0, "total_quantity": 1.2, "order_count": 2}],
            asks=[{"price": 100.5, "total_quantity": 0.8, "order_count": 1}],
            generated_at_ms=1700000000000,
            request_id=request_id,
        )


class FakePersistenceStatus:
    async def get_persistence_status(self, *, request_id: str) -> PersistenceStatusResult:
        assert request_id == "rid-summary-typed-001"
        return PersistenceStatusResult(
            status="ok",
            worker=PersistenceWorkerPayload(
                processed_ticks=12,
                forwarded_executions=0,
                last_execution_id=0,
                last_tick_at=None,
                last_error=None,
                has_last_signal=True,
                tracked_symbols=["BTCUSDT"],
                idempotency={"redis_enabled": False},
                state={"started": True},
            ),
            matching=PersistenceMatchingPayload(
                health=MatchingHealthView(
                    enabled=True,
                    reachable=True,
                    status="ok",
                    service="matching-cpp",
                    version="0.1.0",
                    uptime_seconds=10,
                ),
                stats=MatchingStatsView(
                    enabled=True,
                    live_orders=0,
                    trade_count=0,
                    tracked_orders=0,
                    rejected_orders=0,
                    symbols=0,
                ),
            ),
            stores=PersistenceStoresPayload(
                supabase_enabled=True,
                firebase_enabled=False,
            ),
        )


class FakeInferenceApplication:
    async def status(self) -> InferenceStatusResult:
        return InferenceStatusResult(
            engine_status=InferenceEngineStatus(
                enabled=True,
                ready=True,
                engine="cerberus_signal_transformer_lstm",
                mode="observe",
                metadata={"lookback": 256},
            ),
            active_model=RegisteredModel(
                model_id="cerberus-transformer-lstm",
                version="v1",
                source="gcs",
                symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
                metadata={"best_macro_f1": 0.5001, "horizon": 32},
            ),
            rollout=InferenceRolloutSnapshot(
                configured_mode="primary",
                target_mode="primary",
                effective_mode="observe",
                override_active=False,
                auto_promote_enabled=True,
                force_primary=False,
                promotion_eligible=False,
                blockers=("offline_macro_f1_below_threshold",),
                required_observe_ticks=500,
                compared_ticks=18,
                required_agreement_ratio=0.55,
                agreement_ratio=0.5,
                required_macro_f1=0.58,
                current_macro_f1=0.5001,
                started_at="2026-03-30T00:00:00Z",
                last_transition_at="2026-03-30T00:00:00Z",
            ),
            comparison=InferenceComparisonSnapshot(
                observed_ticks=20,
                compared_ticks=18,
                agreement_count=9,
                divergence_count=9,
            ),
        )


@pytest.mark.asyncio
async def test_summary_application_returns_typed_result_and_serializes_without_contract_change() -> None:
    service = SummaryApplicationService(
        inference_application=FakeInferenceApplication(),
        signal_runtime=FakeSignalRuntime(),
        signal_store=FakeSignalStore(),
        matching_gateway=FakeMatchingGateway(),
        persistence_status=FakePersistenceStatus(),
    )

    result = await service.summary(
        symbol="btcusdt",
        recent_limit=2,
        source="supabase",
        orderbook_depth=5,
        request_id="rid-summary-typed-001",
    )

    assert isinstance(result, SummaryResult)
    assert isinstance(result.signal.payload, SummarySignalPayload)
    assert isinstance(result.recent_signals.payload, SummaryRecentSignalsPayload)

    payload = result.to_dict()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["source"] == "supabase"
    assert payload["signal"]["payload"]["signal"] == "BUY"
    assert payload["signal"]["payload"]["engine"] == "moving_average"
    assert payload["signal"]["payload"]["portfolio"]["execution_gate"] == "review"
    assert payload["signal"]["payload"]["portfolio"]["lead_strategy_label"] == "Rule engine"
    assert payload["signal"]["payload"]["strategy_basket"][1]["engine"] == "cerberus_signal_transformer_lstm"
    assert payload["signal"]["payload"]["portfolio"]["signal_bias"] == "bullish"
    assert payload["signal"]["payload"]["strategy_registry"]["entries"][1]["engine"] == "cerberus_signal_transformer_lstm"
    assert payload["signal"]["payload"]["strategy_registry"]["conflict_policy"] == "review_on_conflict"
    assert payload["recent_signals"]["payload"]["count"] == 1
    assert payload["matching_orderbook"]["payload"]["depth"] == 5
    assert payload["persistence"]["payload"]["worker"]["processed_ticks"] == 12
    assert payload["inference_status"]["payload"]["engine"] == "cerberus_signal_transformer_lstm"
    assert payload["inference_status"]["payload"]["active_model"]["model_id"] == "cerberus-transformer-lstm"
    assert payload["inference_status"]["payload"]["rollout"]["effective_mode"] == "observe"
    assert payload["inference_status"]["payload"]["comparison"]["compared_ticks"] == 18
