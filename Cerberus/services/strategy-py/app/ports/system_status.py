from __future__ import annotations

from typing import Any, Protocol


class RuntimeStatusPort(Protocol):
    def runtime_snapshot(self) -> Any: ...

    def idempotency_snapshot(self) -> dict[str, object]: ...


class StoreStatusPort(Protocol):
    def status(self) -> dict[str, Any]: ...


class MatchingObservabilityPort(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def collect_snapshot(self, *, request_id: str) -> Any: ...
