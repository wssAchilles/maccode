from __future__ import annotations

from dataclasses import dataclass, field

from app.ports import (
    InferenceAuditEvent,
    InferenceComparisonSnapshot,
    InferenceControlResult,
    InferenceEnginePort,
    InferenceEngineStatus,
    InferenceRolloutPort,
    InferenceRolloutSnapshot,
    ModelRegistryPort,
    RegisteredModel,
)


class _StaticInferenceRollout:
    async def restore(self) -> None:
        return

    def effective_mode(self) -> str:
        return "disabled"

    async def record_observation(
        self,
        *,
        symbol: str,
        rule_signal: str,
        inference_decision: object | None,
    ) -> None:
        del symbol, rule_signal, inference_decision

    def snapshot(self) -> InferenceRolloutSnapshot:
        return InferenceRolloutSnapshot(
            configured_mode="disabled",
            target_mode="disabled",
            effective_mode="disabled",
            override_active=False,
            auto_promote_enabled=False,
            force_primary=False,
            promotion_eligible=False,
        )

    def comparison(self) -> InferenceComparisonSnapshot:
        return InferenceComparisonSnapshot(
            observed_ticks=0,
            compared_ticks=0,
            agreement_count=0,
            divergence_count=0,
        )

    def recent_audit_events(self, *, limit: int = 10) -> tuple[InferenceAuditEvent, ...]:
        del limit
        return ()

    async def set_target_mode(
        self,
        *,
        target_mode: str,
        actor: str | None = None,
        reason: str | None = None,
    ) -> None:
        del target_mode, actor, reason

    async def set_active_model(
        self,
        *,
        model: RegisteredModel | None,
        actor: str | None = None,
        reason: str | None = None,
    ) -> None:
        del model, actor, reason

    async def flush(self) -> None:
        return


@dataclass(frozen=True, slots=True)
class InferenceStatusResult:
    engine_status: InferenceEngineStatus
    active_model: RegisteredModel | None
    rollout: InferenceRolloutSnapshot = field(
        default_factory=lambda: InferenceRolloutSnapshot(
            configured_mode="disabled",
            target_mode="disabled",
            effective_mode="disabled",
            override_active=False,
            auto_promote_enabled=False,
            force_primary=False,
            promotion_eligible=False,
        )
    )
    comparison: InferenceComparisonSnapshot = field(
        default_factory=lambda: InferenceComparisonSnapshot(
            observed_ticks=0,
            compared_ticks=0,
            agreement_count=0,
            divergence_count=0,
        )
    )
    audit: tuple[InferenceAuditEvent, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = self.engine_status.to_dict()
        payload["active_model"] = None if self.active_model is None else self.active_model.to_dict()
        payload["rollout"] = self.rollout.to_dict()
        payload["comparison"] = self.comparison.to_dict()
        payload["audit"] = [item.to_dict() for item in self.audit]
        return payload


@dataclass(frozen=True, slots=True)
class InferenceCatalogResult:
    active_model: RegisteredModel | None
    models: tuple[RegisteredModel, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "count": len(self.models),
            "active_model": None if self.active_model is None else self.active_model.to_dict(),
            "models": [item.to_dict() for item in self.models],
        }


class InferenceApplicationService:
    def __init__(
        self,
        *,
        engine: InferenceEnginePort,
        model_registry: ModelRegistryPort,
        rollout: InferenceRolloutPort | None = None,
    ) -> None:
        self._engine = engine
        self._model_registry = model_registry
        self._rollout = rollout or _StaticInferenceRollout()

    async def startup(self) -> None:
        await self._rollout.restore()

    async def shutdown(self) -> None:
        await self._rollout.flush()

    async def status(self) -> InferenceStatusResult:
        rollout = self._rollout.snapshot()
        engine_status = await self._engine.status()
        engine_status = InferenceEngineStatus(
            enabled=engine_status.enabled,
            ready=engine_status.ready,
            engine=engine_status.engine,
            mode=rollout.effective_mode,
            reason=engine_status.reason,
            metadata=dict(engine_status.metadata),
        )
        return InferenceStatusResult(
            engine_status=engine_status,
            active_model=self._model_registry.active_model(),
            rollout=rollout,
            comparison=self._rollout.comparison(),
            audit=self._rollout.recent_audit_events(),
        )

    def models(self) -> InferenceCatalogResult:
        return InferenceCatalogResult(
            active_model=self._model_registry.active_model(),
            models=self._model_registry.list_models(),
        )

    def audit(self, *, limit: int = 20) -> dict[str, object]:
        return {
            "count": len(self._rollout.recent_audit_events(limit=limit)),
            "events": [item.to_dict() for item in self._rollout.recent_audit_events(limit=limit)],
        }

    async def promote(
        self,
        *,
        actor: str | None = None,
        reason: str | None = None,
    ) -> InferenceControlResult:
        await self._rollout.set_target_mode(
            target_mode="primary",
            actor=actor,
            reason=reason,
        )
        return await self._build_control_result(
            action="promote",
            actor=actor,
            reason=reason,
            requested_mode="primary",
        )

    async def rollback(
        self,
        *,
        actor: str | None = None,
        reason: str | None = None,
    ) -> InferenceControlResult:
        await self._rollout.set_target_mode(
            target_mode="observe",
            actor=actor,
            reason=reason,
        )
        return await self._build_control_result(
            action="rollback",
            actor=actor,
            reason=reason,
            requested_mode="observe",
        )

    async def activate_model(
        self,
        *,
        model_id: str,
        version: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
    ) -> InferenceControlResult:
        selected_model = self._model_registry.activate_model(
            model_id=model_id,
            version=version,
        )
        await self._rollout.set_active_model(
            model=selected_model,
            actor=actor,
            reason=reason,
        )
        return await self._build_control_result(
            action="activate_model",
            actor=actor,
            reason=reason,
            selected_model=selected_model,
        )

    async def _build_control_result(
        self,
        *,
        action: str,
        actor: str | None,
        reason: str | None,
        requested_mode: str | None = None,
        selected_model: RegisteredModel | None = None,
    ) -> InferenceControlResult:
        status = await self.status()
        rollout = status.rollout
        accepted = True
        message = "inference rollout updated"
        if action == "promote":
            if rollout.effective_mode == "primary":
                message = "inference rollout promoted to primary"
            elif rollout.target_mode == "primary":
                accepted = False
                message = "primary rollout requested and held by promotion gates"
        elif action == "rollback":
            message = "inference rollout reverted to observe"
        elif action == "activate_model":
            message = "active inference model changed"
        return InferenceControlResult(
            accepted=accepted,
            action=action,
            message=message,
            actor=actor,
            reason=reason,
            requested_mode=requested_mode,
            selected_model=selected_model,
            active_model=status.active_model,
            rollout=rollout,
            comparison=status.comparison,
            audit=status.audit,
            models=self._model_registry.list_models(),
        )
