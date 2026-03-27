from __future__ import annotations

from typing import Any, Protocol


class PersistenceStatusPort(Protocol):
    async def get_persistence_status(self, *, request_id: str) -> dict[str, Any]: ...

