from __future__ import annotations

from app.application import InferenceApplicationService


class InferenceService:
    def __init__(self, *, application: InferenceApplicationService) -> None:
        self._application = application

    async def status(self) -> dict[str, object]:
        return (await self._application.status()).to_dict()

    def models(self) -> dict[str, object]:
        return self._application.models().to_dict()

    def audit(self, *, limit: int = 20) -> dict[str, object]:
        return self._application.audit(limit=limit)
