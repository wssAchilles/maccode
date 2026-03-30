from __future__ import annotations

import pytest

from app.application import SignalApplicationService
from app.infrastructure.inference_rollout import RuntimeInferenceRolloutManager
from app.ports import RegisteredModel
from app.schemas import Signal, TickEvent


class FakeSignalRuntime:
    def __init__(self) -> None:
        self.current_signal: Signal | None = None
        self.evaluated_tick: TickEvent | None = None
        self.stored_signal: Signal | None = None
        self.processed_count = 0

    def read_current_signal(self) -> Signal | None:
        return self.current_signal

    def evaluate_tick(self, tick: TickEvent) -> tuple[Signal, str]:
        self.evaluated_tick = tick
        signal = Signal(
            strategy_id="default",
            symbol=tick.symbol,
            signal="BUY",
            confidence=0.73,
        )
        return signal, "sig-001"

    def build_signal_id(self, tick: TickEvent, signal: Signal) -> str:
        return f"{signal.strategy_id}:{signal.symbol}:{tick.event_time}:{signal.signal}"

    def store_current_signal(self, signal: Signal) -> None:
        self.stored_signal = signal

    def record_tick_processed(self) -> None:
        self.processed_count += 1


class FakeSignalStore:
    async def list_recent(
        self,
        limit: int,
        source: str = "auto",
    ) -> tuple[str, list[object]]:
        return source, []


class FakeSignalClaims:
    def __init__(self, *, should_claim: bool = True) -> None:
        self.should_claim = should_claim
        self.claimed_ids: list[str] = []
        self.released_ids: list[str] = []

    async def claim_signal(self, signal_id: str) -> bool:
        self.claimed_ids.append(signal_id)
        return self.should_claim

    async def release_signal_claim(self, signal_id: str) -> None:
        self.released_ids.append(signal_id)


class FakeSignalEventFlow:
    def __init__(self) -> None:
        self.calls: list[tuple[Signal, TickEvent, str]] = []

    async def publish_signal_flow(
        self,
        signal: Signal,
        tick: TickEvent,
        signal_id: str,
    ) -> None:
        self.calls.append((signal, tick, signal_id))


class FakeSignalPublisher:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.published: list[Signal] = []

    async def publish_signal(self, signal: Signal) -> None:
        if self.should_fail:
            raise RuntimeError("publisher failed")
        self.published.append(signal)


class FakeInferenceEngine:
    def __init__(
        self,
        *,
        signal: str = "SELL",
        confidence: float = 0.91,
        engine: str = "shadow-model",
    ) -> None:
        self.signal = signal
        self.confidence = confidence
        self.engine = engine
        self.calls: list[TickEvent] = []

    async def infer_signal(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        event_time: str,
    ):
        tick = TickEvent(
            symbol=symbol,
            price=price,
            quantity=quantity,
            event_time=event_time,
        )
        self.calls.append(tick)
        return type(
            "InferenceDecisionValue",
            (),
            {
                "strategy_id": "inference",
                "signal": self.signal,
                "confidence": self.confidence,
                "engine": self.engine,
                "model_id": "model-001",
                "model_version": "v1",
                "metadata": {"source": "test"},
            },
        )()

    async def status(self):
        raise AssertionError("status should not be used in signal application tests")


def _sample_tick() -> TickEvent:
    return TickEvent(
        symbol="BTCUSDT",
        price=100.0,
        quantity=0.25,
        event_time="2026-03-27T12:00:00Z",
    )


@pytest.mark.asyncio
async def test_signal_application_ingest_tick_runs_full_dispatch_flow() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims()
    event_flow = FakeSignalEventFlow()
    publisher_one = FakeSignalPublisher()
    publisher_two = FakeSignalPublisher()
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher_one, publisher_two),
    )

    decision = await service.ingest_tick(_sample_tick())

    assert decision.signal.signal == "BUY"
    assert decision.context.metadata["signal_id"] == "sig-001"
    assert decision.context.metadata["dispatch_state"] == "accepted"
    assert runtime.stored_signal is not None
    assert runtime.processed_count == 1
    assert claims.claimed_ids == ["sig-001"]
    assert claims.released_ids == []
    assert len(event_flow.calls) == 1
    assert len(publisher_one.published) == 1
    assert len(publisher_two.published) == 1


@pytest.mark.asyncio
async def test_signal_application_ingest_tick_skips_side_effects_when_claim_denied() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims(should_claim=False)
    event_flow = FakeSignalEventFlow()
    publisher = FakeSignalPublisher()
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher,),
    )

    decision = await service.ingest_tick(_sample_tick())

    assert decision.context.metadata["dispatch_state"] == "duplicate"
    assert runtime.stored_signal is None
    assert runtime.processed_count == 0
    assert claims.claimed_ids == ["sig-001"]
    assert claims.released_ids == []
    assert event_flow.calls == []
    assert publisher.published == []


@pytest.mark.asyncio
async def test_signal_application_releases_claim_when_publisher_fails() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims()
    event_flow = FakeSignalEventFlow()
    publisher = FakeSignalPublisher(should_fail=True)
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher,),
    )

    with pytest.raises(RuntimeError, match="publisher failed"):
        await service.ingest_tick(_sample_tick())

    assert runtime.stored_signal is not None
    assert runtime.processed_count == 0
    assert claims.claimed_ids == ["sig-001"]
    assert claims.released_ids == ["sig-001"]
    assert len(event_flow.calls) == 1


@pytest.mark.asyncio
async def test_signal_application_uses_inference_as_primary_when_enabled() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims()
    event_flow = FakeSignalEventFlow()
    publisher = FakeSignalPublisher()
    inference = FakeInferenceEngine(signal="SELL", confidence=0.91, engine="moving_average_baseline")
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher,),
        inference_engine=inference,
        inference_mode="primary",
    )

    decision = await service.ingest_tick(_sample_tick())

    assert decision.signal.signal == "SELL"
    assert decision.signal.strategy_id == "inference"
    assert decision.context.engine == "moving_average_baseline"
    assert decision.context.metadata["decision_source"] == "inference"
    assert runtime.stored_signal is not None
    assert runtime.stored_signal.signal == "SELL"
    assert inference.calls


@pytest.mark.asyncio
async def test_signal_application_keeps_rule_signal_when_inference_is_observe_only() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims()
    event_flow = FakeSignalEventFlow()
    publisher = FakeSignalPublisher()
    inference = FakeInferenceEngine(signal="SELL", confidence=0.91, engine="shadow-model")
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher,),
        inference_engine=inference,
        inference_mode="observe",
    )

    decision = await service.ingest_tick(_sample_tick())

    assert decision.signal.signal == "BUY"
    assert decision.context.engine == "moving_average"
    assert decision.context.metadata["decision_source"] == "rule_engine"
    assert decision.context.metadata["inference"]["engine"] == "shadow-model"


@pytest.mark.asyncio
async def test_signal_application_respects_rollout_holdback_before_using_primary() -> None:
    runtime = FakeSignalRuntime()
    claims = FakeSignalClaims()
    event_flow = FakeSignalEventFlow()
    publisher = FakeSignalPublisher()
    inference = FakeInferenceEngine(signal="SELL", confidence=0.91, engine="shadow-model")
    rollout = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=RegisteredModel(
            model_id="cerberus-transformer-lstm",
            version="v1",
            source="gcs",
            metadata={"best_macro_f1": 0.60},
        ),
        started_at=1_711_767_200.0,
        required_macro_f1=0.55,
        required_observe_ticks=3,
        required_agreement_ratio=0.55,
        force_primary=False,
    )
    service = SignalApplicationService(
        runtime=runtime,
        signal_store=FakeSignalStore(),
        signal_claims=claims,
        event_flow=event_flow,
        publishers=(publisher,),
        inference_engine=inference,
        inference_mode="primary",
        inference_rollout=rollout,
    )

    decision = await service.ingest_tick(_sample_tick())

    assert rollout.effective_mode() == "observe"
    assert decision.signal.signal == "BUY"
    assert decision.context.metadata["inference_mode"] == "observe"
