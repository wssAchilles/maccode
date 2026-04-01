from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.strategy_orchestration_service import StrategyOrchestrationService


class StrategyOrchestrationActionRequest(BaseModel):
    actor: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


class StrategyOrchestrationEntryUpdateRequest(StrategyOrchestrationActionRequest):
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    observe_weight: float | None = Field(default=None, ge=0)
    primary_weight: float | None = Field(default=None, ge=0)
    symbol_coverage: list[str] | None = None


class StrategyOrchestrationPolicyUpdateRequest(StrategyOrchestrationActionRequest):
    conflict_policy: str | None = Field(default=None, max_length=80)
    downgrade_policy: str | None = Field(default=None, max_length=80)


def build_strategy_orchestration_router(service: StrategyOrchestrationService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/strategy/orchestration/status")
    async def strategy_orchestration_status() -> dict[str, object]:
        return await service.status()

    @router.get("/api/v1/strategy/orchestration/audit")
    async def strategy_orchestration_audit(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
        return service.audit(limit=limit)

    @router.post("/api/v1/strategy/orchestration/entries/{strategy_id}")
    async def update_strategy_orchestration_entry(
        strategy_id: str,
        body: StrategyOrchestrationEntryUpdateRequest,
    ) -> dict[str, object]:
        try:
            return await service.update_entry(
                strategy_id=strategy_id,
                enabled=body.enabled,
                priority=body.priority,
                observe_weight=body.observe_weight,
                primary_weight=body.primary_weight,
                symbol_coverage=(
                    tuple(str(item).strip().upper() for item in body.symbol_coverage if str(item).strip())
                    if body.symbol_coverage is not None
                    else None
                ),
                actor=body.actor,
                reason=body.reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/api/v1/strategy/orchestration/policies")
    async def update_strategy_orchestration_policies(
        body: StrategyOrchestrationPolicyUpdateRequest,
    ) -> dict[str, object]:
        return await service.update_policies(
            conflict_policy=body.conflict_policy,
            downgrade_policy=body.downgrade_policy,
            actor=body.actor,
            reason=body.reason,
        )

    return router
