from __future__ import annotations

from typing import Any

from app.api.system_helpers import build_persistence_status
from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort


class WorkerPersistenceStatusAdapter:
    def __init__(
        self,
        runtime_status: RuntimeStatusPort,
        signal_store_status: StoreStatusPort,
        matching_observability: MatchingObservabilityPort,
    ) -> None:
        self._runtime_status = runtime_status
        self._signal_store_status = signal_store_status
        self._matching_observability = matching_observability

    async def get_persistence_status(self, *, request_id: str) -> dict[str, Any]:
        return await build_persistence_status(
            self._runtime_status,
            self._signal_store_status,
            self._matching_observability,
            request_id=request_id,
        )
