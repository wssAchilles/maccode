from __future__ import annotations

from typing import Any

import pytest

from app.infrastructure.strategy_orchestration import RuntimeStrategyOrchestrationManager


class InMemoryStateStore:
    backend_name = "memory"

    def __init__(self) -> None:
        self.saved: dict[str, Any] | None = None

    async def load_state(self) -> dict[str, Any] | None:
        return self.saved

    async def save_state(self, state: dict[str, Any]) -> None:
        self.saved = state


@pytest.mark.asyncio
async def test_strategy_orchestration_entry_controls_include_conflicts_and_downgrade() -> None:
    store = InMemoryStateStore()
    manager = RuntimeStrategyOrchestrationManager(state_store=store)

    await manager.startup()

    initial = manager.snapshot(
        tracked_symbols=("BTCUSDT", "ETHUSDT"),
        inference_runtime_enabled=True,
        inference_model_symbols=("BTCUSDT", "ETHUSDT"),
        inference_engine_name="cerberus_signal_transformer_lstm",
    )
    default_entry = next(item for item in initial.entries if item.strategy_id == "default")
    assert default_entry.conflict_targets == ("inference",)
    assert default_entry.downgrade_action == "review"

    result = await manager.update_entry(
        strategy_id="default",
        tracked_symbols=("BTCUSDT", "ETHUSDT"),
        inference_runtime_enabled=True,
        inference_model_symbols=("BTCUSDT",),
        inference_engine_name="cerberus_signal_transformer_lstm",
        conflict_targets=("inference",),
        downgrade_action="hold",
        actor="tester",
        reason="tighten review policy",
    )

    assert result.accepted is True
    updated_entry = next(item for item in result.snapshot.entries if item.strategy_id == "default")
    assert updated_entry.conflict_targets == ("inference",)
    assert updated_entry.downgrade_action == "hold"
    assert store.saved is not None
    persisted_entry = next(item for item in store.saved["entries"] if item["strategy_id"] == "default")
    assert persisted_entry["conflict_targets"] == ["inference"]
    assert persisted_entry["downgrade_action"] == "hold"
