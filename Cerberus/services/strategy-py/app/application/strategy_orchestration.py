from __future__ import annotations

from dataclasses import dataclass

from app.application.inference import InferenceApplicationService
from app.ports import (
    StrategyOrchestrationControlResult,
    StrategyOrchestrationPort,
    StrategyOrchestrationSnapshot,
)
from app.ports.signal import SignalRuntimePort


@dataclass(frozen=True, slots=True)
class StrategyOrchestrationStatusResult:
    snapshot: StrategyOrchestrationSnapshot
    request_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = self.snapshot.to_dict()
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        return payload


class StrategyOrchestrationApplicationService:
    def __init__(
        self,
        *,
        orchestration: StrategyOrchestrationPort,
        signal_runtime: SignalRuntimePort,
        inference_application: InferenceApplicationService,
    ) -> None:
        self._orchestration = orchestration
        self._signal_runtime = signal_runtime
        self._inference_application = inference_application

    async def status(
        self, *, request_id: str | None = None
    ) -> StrategyOrchestrationStatusResult:
        return StrategyOrchestrationStatusResult(
            snapshot=await self._snapshot(),
            request_id=request_id,
        )

    def audit(self, *, limit: int = 20, request_id: str | None = None) -> dict[str, object]:
        events = self._orchestration.audit(limit=limit)
        payload = {
            "count": len(events),
            "events": [item.to_dict() for item in events],
        }
        if request_id is not None:
            payload["request_id"] = request_id
        return payload

    async def update_entry(
        self,
        *,
        strategy_id: str,
        enabled: bool | None = None,
        priority: int | None = None,
        observe_weight: float | None = None,
        primary_weight: float | None = None,
        symbol_coverage: tuple[str, ...] | None = None,
        conflict_targets: tuple[str, ...] | None = None,
        downgrade_action: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> StrategyOrchestrationControlResult:
        context = await self._context()
        return await self._orchestration.update_entry(
            strategy_id=strategy_id,
            enabled=enabled,
            priority=priority,
            observe_weight=observe_weight,
            primary_weight=primary_weight,
            symbol_coverage=symbol_coverage,
            conflict_targets=conflict_targets,
            downgrade_action=downgrade_action,
            actor=actor,
            reason=reason,
            request_id=request_id,
            **context,
        )

    async def update_policies(
        self,
        *,
        conflict_policy: str | None = None,
        downgrade_policy: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> StrategyOrchestrationControlResult:
        context = await self._context()
        return await self._orchestration.update_policies(
            conflict_policy=conflict_policy,
            downgrade_policy=downgrade_policy,
            actor=actor,
            reason=reason,
            request_id=request_id,
            **context,
        )

    async def _snapshot(self) -> StrategyOrchestrationSnapshot:
        context = await self._context()
        return self._orchestration.snapshot(**context)

    async def _context(self) -> dict[str, object]:
        inference_status = await self._inference_application.status()
        tracked_symbols = self._signal_runtime.tracked_symbols()
        active_model = inference_status.active_model
        return {
            "tracked_symbols": tracked_symbols,
            "inference_runtime_enabled": inference_status.engine_status.enabled,
            "inference_model_symbols": active_model.symbols if active_model is not None else (),
            "inference_engine_name": inference_status.engine_status.engine,
        }
