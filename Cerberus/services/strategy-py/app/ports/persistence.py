from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.system_status_query.persistence import PersistenceStatusResult


class PersistenceStatusPort(Protocol):
    async def get_persistence_status(self, *, request_id: str) -> PersistenceStatusResult: ...
