from __future__ import annotations

from app.application import InferenceApplicationService


class InferenceService:
    def __init__(self, *, application: InferenceApplicationService) -> None:
        self._application = application

    async def startup(self) -> None:
        await self._application.startup()

    async def shutdown(self) -> None:
        await self._application.shutdown()

    async def status(self) -> dict[str, object]:
        return (await self._application.status()).to_dict()

    def models(self) -> dict[str, object]:
        return self._application.models().to_dict()

    def audit(self, *, limit: int = 20) -> dict[str, object]:
        return self._application.audit(limit=limit)

    async def promote(self, *, actor: str | None = None, reason: str | None = None) -> dict[str, object]:
        return (await self._application.promote(actor=actor, reason=reason)).to_dict()

    async def rollback(self, *, actor: str | None = None, reason: str | None = None) -> dict[str, object]:
        return (await self._application.rollback(actor=actor, reason=reason)).to_dict()

    async def activate_model(
        self,
        *,
        model_id: str,
        version: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        return (
            await self._application.activate_model(
                model_id=model_id,
                version=version,
                actor=actor,
                reason=reason,
            )
        ).to_dict()
