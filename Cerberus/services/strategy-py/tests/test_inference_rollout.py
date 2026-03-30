from __future__ import annotations

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


def test_rollout_manager_holds_primary_until_promotion_gates_pass() -> None:
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

    manager.record_observation(
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

    manager.record_observation(
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


def test_rollout_manager_keeps_primary_held_when_macro_f1_is_below_threshold() -> None:
    manager = RuntimeInferenceRolloutManager(
        configured_mode="primary",
        active_model=_active_model(macro_f1=0.50),
        started_at=1_711_767_200.0,
        required_macro_f1=0.58,
        required_observe_ticks=1,
        required_agreement_ratio=0.5,
        force_primary=False,
    )

    manager.record_observation(
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


def test_rollout_manager_emits_milestone_and_blocker_change_audit_events() -> None:
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
        manager.record_observation(
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
