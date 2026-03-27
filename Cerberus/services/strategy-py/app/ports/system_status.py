from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.matching_observability import MatchingSnapshot
    from app.redis_worker.runtime_state import WorkerRuntimeSnapshot
    from app.system_status_query.persistence import PersistenceStoresPayload


class RuntimeStatusPort(Protocol):
    def runtime_snapshot(self) -> WorkerRuntimeSnapshot: ...

    def idempotency_snapshot(self) -> dict[str, object]: ...


class StoreStatusPort(Protocol):
    def status(self) -> PersistenceStoresPayload: ...


class MatchingObservabilityPort(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def collect_snapshot(self, *, request_id: str) -> MatchingSnapshot: ...
