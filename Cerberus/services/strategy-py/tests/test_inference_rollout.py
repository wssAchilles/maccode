from __future__ import annotations

import pytest

from app.infrastructure.inference_rollout import RuntimeInferenceRolloutManager
from app.ports import InferenceDecision, RegisteredModel


def _active_model(*, macro_f1: float = 0.62) -> RegisteredModel:
    return RegisteredModel(
        model_id="cerberus-transformer-lstm",
        version="v1",
        source="gcs",
        symbols=("BTCUSDT", "ETHUSDT"),
        metadata={"best_macro_f1": macro_f1},
    )


class FakeStateStore:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.payload = payload
        self.saved: dict[str, object] | None = None

    @property
    def backend_name(self) -> str:
        return "redis"

    async def load_state(self) -> dict[str, object] | None:
        return self.payload

    async def save_state(self, state: dict[str, object]) -> None:
        self.saved = state


@pytest.mark.asyncio
async def test_rollout_manager_holds_primary_until_promotion_gates_pass() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=2,
        required_agreement_ratio=0.5,
        force_primary=False,
    )

    assert manager.effective_mode() == "observe"
    assert "insufficient_observe_ticks" in manager.snapshot().blockers
    assert manager.snapshot().target_mode == "primary"

    await manager.record_observation(
        symbol="BTCUSDT",
        rule_signal="BUY",
        inference_decision=InferenceDecision(
            strategy_id="inference",
            signal="BUY",
            confidence=0.88,
            engine="cerberus_signal_transformer_lstm",
        ),
    )
    assert manager.effective_mode() == "observe"

    await manager.record_observation(
        symbol="BTCUSDT",
        rule_signal="SELL",
        inference_decision=InferenceDecision(
            strategy_id="inference",
            signal="SELL",
            confidence=0.77,
            engine="cerberus_signal_transformer_lstm",
        ),
    )

    snapshot = manager.snapshot()
    comparison = manager.comparison()

    assert manager.effective_mode() == "primary"
    assert snapshot.promotion_eligible is True
    assert snapshot.blockers == ()
    assert comparison.compared_ticks == 2
    assert comparison.agreement_ratio == 1.0
    assert any(event.event_type == "rollout_transition" for event in manager.recent_audit_events())


@pytest.mark.asyncio
async def test_rollout_manager_keeps_primary_held_when_macro_f1_is_below_threshold() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.50),
        started_at=1_711_767_200.0,
        required_macro_f1=0.58,
        required_observe_ticks=1,
        required_agreement_ratio=0.5,
        force_primary=False,
    )

    await manager.record_observation(
        symbol="BTCUSDT",
        rule_signal="BUY",
        inference_decision=InferenceDecision(
            strategy_id="inference",
            signal="BUY",
            confidence=0.88,
            engine="cerberus_signal_transformer_lstm",
        ),
    )

    snapshot = manager.snapshot()

    assert manager.effective_mode() == "observe"
    assert "offline_macro_f1_below_threshold" in snapshot.blockers


@pytest.mark.asyncio
async def test_rollout_manager_emits_milestone_and_blocker_change_audit_events() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=10,
        required_agreement_ratio=0.5,
        force_primary=False,
    )

    for _ in range(10):
        await manager.record_observation(
            symbol="BTCUSDT",
            rule_signal="BUY",
            inference_decision=InferenceDecision(
                strategy_id="inference",
                signal="BUY",
                confidence=0.9,
                engine="cerberus_signal_transformer_lstm",
            ),
        )

    events = manager.recent_audit_events(limit=10)
    event_types = [event.event_type for event in events]

    assert "comparison_milestone" in event_types
    assert "rollout_blockers_changed" in event_types
    assert "rollout_transition" in event_types


@pytest.mark.asyncio
async def test_rollout_manager_restores_persisted_state_and_emits_resume_event() -> None:
    store = FakeStateStore(
        payload={
            "schema_version": 1,
            "configured_mode": "primary",
            "force_primary": False,
            "active_model": {"model_id": "cerberus-transformer-lstm", "version": "v1"},
            "started_at": "2026-03-30T00:00:00Z",
            "last_transition_at": "2026-03-30T01:00:00Z",
            "effective_mode": "observe",
            "last_blockers": ["insufficient_observe_ticks"],
            "observed_ticks": 12,
            "compared_ticks": 10,
            "agreement_count": 6,
            "divergence_count": 4,
            "rule_signal_counts": {"BUY": 10},
            "inference_signal_counts": {"BUY": 6, "SELL": 4},
            "symbol_counters": {
                "BTCUSDT": {
                    "compared_ticks": 10,
                    "agreement_count": 6,
                    "divergence_count": 4,
                }
            },
            "emitted_milestones": [10],
            "audit_events": [
                {
                    "event_type": "comparison_milestone",
                    "created_at": "2026-03-30T00:30:00Z",
                    "message": "inference comparison reached 10 compared ticks",
                    "metadata": {"milestone": 10},
                }
            ],
            "last_persisted_at": "2026-03-30T01:02:00Z",
        }
    )
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=20,
        required_agreement_ratio=0.5,
        force_primary=False,
        state_store=store,
    )

    await manager.restore()

    snapshot = manager.snapshot()
    comparison = manager.comparison()
    events = manager.recent_audit_events(limit=5)

    assert snapshot.state_restored is True
    assert snapshot.state_backend == "redis"
    assert snapshot.last_persisted_at
    assert snapshot.started_at == "2026-03-30T00:00:00Z"
    assert comparison.compared_ticks == 10
    assert comparison.symbols[0].symbol == "BTCUSDT"
    assert events[-1].event_type == "rollout_resumed"
    assert store.saved is not None


@pytest.mark.asyncio
async def test_rollout_manager_skips_restore_when_model_identity_changes() -> None:
    store = FakeStateStore(
        payload={
            "schema_version": 1,
            "configured_mode": "primary",
            "force_primary": False,
            "active_model": {"model_id": "another-model", "version": "v1"},
        }
    )
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=2,
        required_agreement_ratio=0.5,
        force_primary=False,
        state_store=store,
    )

    await manager.restore()

    events = manager.recent_audit_events(limit=5)
    assert any(event.event_type == "rollout_restore_skipped" for event in events)
    assert manager.snapshot().state_restored is False


@pytest.mark.asyncio
async def test_rollout_manager_allows_manual_promotion_request_from_observe_mode() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="observe",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=5,
        required_agreement_ratio=0.5,
        force_primary=False,
    )

    await manager.set_target_mode(
        target_mode="primary",
        actor="operator@example.com",
        reason="request controlled promotion",
    )

    snapshot = manager.snapshot()
    events = manager.recent_audit_events(limit=10)

    assert snapshot.configured_mode == "observe"
    assert snapshot.target_mode == "primary"
    assert snapshot.override_active is True
    assert snapshot.effective_mode == "observe"
    assert any(event.event_type == "rollout_target_changed" for event in events)
    assert any(event.event_type == "rollout_holdback" for event in events)


@pytest.mark.asyncio
async def test_rollout_manager_rolls_back_to_observe_and_clears_primary_effective_mode() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=1,
        required_agreement_ratio=0.5,
        force_primary=False,
    )
    await manager.record_observation(
        symbol="BTCUSDT",
        rule_signal="BUY",
        inference_decision=InferenceDecision(
            strategy_id="inference",
            signal="BUY",
            confidence=0.9,
            engine="cerberus_signal_transformer_lstm",
        ),
    )
    assert manager.effective_mode() == "primary"

    await manager.set_target_mode(
        target_mode="observe",
        actor="operator@example.com",
        reason="safety rollback",
    )

    snapshot = manager.snapshot()
    assert snapshot.target_mode == "observe"
    assert snapshot.override_active is True
    assert snapshot.effective_mode == "observe"


@pytest.mark.asyncio
async def test_rollout_manager_resets_comparison_counters_when_active_model_changes() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.61),
        started_at=1_711_767_200.0,
        required_macro_f1=0.6,
        required_observe_ticks=1,
        required_agreement_ratio=0.5,
        force_primary=False,
    )
    await manager.record_observation(
        symbol="BTCUSDT",
        rule_signal="BUY",
        inference_decision=InferenceDecision(
            strategy_id="inference",
            signal="BUY",
            confidence=0.9,
            engine="cerberus_signal_transformer_lstm",
        ),
    )
    assert manager.comparison().compared_ticks == 1

    await manager.set_active_model(
        model=RegisteredModel(
            model_id="cerberus-transformer-lstm",
            version="v2",
            source="gcs",
            symbols=("BTCUSDT", "ETHUSDT"),
            metadata={"best_macro_f1": 0.67},
        ),
        actor="operator@example.com",
        reason="promote better candidate",
    )

    snapshot = manager.snapshot()
    comparison = manager.comparison()
    events = manager.recent_audit_events(limit=10)

    assert comparison.compared_ticks == 0
    assert comparison.observed_ticks == 0
    assert snapshot.current_macro_f1 == pytest.approx(0.67)
    assert any(event.event_type == "active_model_changed" for event in events)
