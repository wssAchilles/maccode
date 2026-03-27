from __future__ import annotations

from app.application import SystemStatusApplicationService


class SystemStatusService:
    def __init__(self, *, application: SystemStatusApplicationService) -> None:
        self._application = application

    async def ready(self, *, request_id: str) -> tuple[int, dict[str, object]]:
        result = await self._application.ready(
            request_id=request_id,
        )
        return result.status_code, result.payload.to_dict()

    async def metrics_lines(self, *, request_id: str) -> list[str]:
        return await self._application.metrics_lines(
            request_id=request_id,
        )

    async def persistence(self, *, request_id: str) -> dict[str, object]:
        result = await self._application.persistence_status(
            request_id=request_id,
        )
        return result.to_dict()
