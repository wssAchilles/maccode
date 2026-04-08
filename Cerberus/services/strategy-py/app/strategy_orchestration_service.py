from __future__ import annotations

from app.application import StrategyOrchestrationApplicationService


class StrategyOrchestrationService:
    def __init__(self, *, application: StrategyOrchestrationApplicationService) -> None:
        self._application = application

    async def status(self, *, request_id: str | None = None) -> dict[str, object]:
        return (await self._application.status(request_id=request_id)).to_dict()

    def audit(self, *, limit: int = 20, request_id: str | None = None) -> dict[str, object]:
        return self._application.audit(limit=limit, request_id=request_id)

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
    ) -> dict[str, object]:
        return (
            await self._application.update_entry(
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
            )
        ).to_dict()

    async def update_policies(
        self,
        *,
        conflict_policy: str | None = None,
        downgrade_policy: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, object]:
        return (
            await self._application.update_policies(
                conflict_policy=conflict_policy,
                downgrade_policy=downgrade_policy,
                actor=actor,
                reason=reason,
                request_id=request_id,
            )
        ).to_dict()
