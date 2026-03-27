from __future__ import annotations

from app.application import SystemStatusApplicationService
from app.system_status_query import PersistenceStatusResult


class WorkerPersistenceStatusAdapter:
    def __init__(
        self,
        application: SystemStatusApplicationService,
    ) -> None:
        self._application = application

    async def get_persistence_status(self, *, request_id: str) -> PersistenceStatusResult:
        return await self._application.persistence_status(
            request_id=request_id,
        )
