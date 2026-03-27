from __future__ import annotations

from app.matching_observability import collect_matching_snapshot
from app.ports import MatchingGatewayPort
from app.redis_worker import RedisMarketWorker
from app.signal_store import SignalStore


class WorkerRuntimeStatusAdapter:
    def __init__(self, worker: RedisMarketWorker) -> None:
        self._worker = worker

    def runtime_snapshot(self) -> object:
        return self._worker.runtime_snapshot()

    def idempotency_snapshot(self) -> dict[str, object]:
        return self._worker.idempotency_snapshot()


class SignalStoreStatusAdapter:
    def __init__(self, signal_store: SignalStore) -> None:
        self._signal_store = signal_store

    def status(self) -> dict[str, object]:
        return self._signal_store.status()


class MatchingObservabilityAdapter:
    def __init__(self, gateway: MatchingGatewayPort) -> None:
        self._gateway = gateway

    @property
    def enabled(self) -> bool:
        return self._gateway.enabled

    async def collect_snapshot(self, *, request_id: str) -> object:
        return await collect_matching_snapshot(self._gateway, request_id=request_id)
