from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.ports import MatchingObservabilityPort, RuntimeStatusPort, StoreStatusPort
from app.schemas import MatchingHealthView, MatchingStatsView

from .worker_state import build_worker_state


@dataclass(frozen=True, slots=True)
class PersistenceWorkerPayload:
    processed_ticks: int
    forwarded_executions: int
    last_execution_id: int
    last_tick_at: str | None
    last_error: str | None
    has_last_signal: bool
    tracked_symbols: list[str]
    idempotency: dict[str, object]
    state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "processed_ticks": self.processed_ticks,
            "forwarded_executions": self.forwarded_executions,
            "last_execution_id": self.last_execution_id,
            "last_tick_at": self.last_tick_at,
            "last_error": self.last_error,
            "has_last_signal": self.has_last_signal,
            "tracked_symbols": self.tracked_symbols,
            "idempotency": self.idempotency,
            **self.state,
        }


@dataclass(frozen=True, slots=True)
class PersistenceMatchingPayload:
    health: MatchingHealthView
    stats: MatchingStatsView

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health.model_dump(),
            "stats": self.stats.model_dump(),
        }


@dataclass(frozen=True, slots=True)
class PersistenceStoresPayload:
    supabase_enabled: bool
    firebase_enabled: bool
    supabase_table: str | None = None
    firebase_collection: str | None = None
    extras: dict[str, Any] | None = None

    @classmethod
    def from_status(cls, status: Mapping[str, Any]) -> PersistenceStoresPayload:
        known_keys = {
            "supabase_enabled",
            "firebase_enabled",
            "supabase_table",
            "firebase_collection",
        }
        extras = {key: value for key, value in status.items() if key not in known_keys}
        return cls(
            supabase_enabled=bool(status.get("supabase_enabled", False)),
            firebase_enabled=bool(status.get("firebase_enabled", False)),
            supabase_table=_coerce_optional_str(status.get("supabase_table")),
            firebase_collection=_coerce_optional_str(status.get("firebase_collection")),
            extras=extras or None,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "supabase_enabled": self.supabase_enabled,
            "firebase_enabled": self.firebase_enabled,
            "supabase_table": self.supabase_table,
            "firebase_collection": self.firebase_collection,
        }
        if self.extras:
            payload.update(self.extras)
        return payload


@dataclass(frozen=True, slots=True)
class PersistenceStatusResult:
    status: str
    worker: PersistenceWorkerPayload
    matching: PersistenceMatchingPayload
    stores: PersistenceStoresPayload

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "worker": self.worker.to_dict(),
            "matching": self.matching.to_dict(),
            "stores": self.stores.to_dict(),
        }


async def build_persistence_status(
    runtime_status: RuntimeStatusPort,
    signal_store_status: StoreStatusPort,
    matching_observability: MatchingObservabilityPort,
    *,
    request_id: str,
) -> PersistenceStatusResult:
    snapshot = runtime_status.runtime_snapshot()
    matching_snapshot = await matching_observability.collect_snapshot(request_id=request_id)
    idempotency = runtime_status.idempotency_snapshot()
    stores = PersistenceStoresPayload.from_status(signal_store_status.status())
    worker = PersistenceWorkerPayload(
        processed_ticks=snapshot.processed_ticks,
        forwarded_executions=snapshot.forwarded_executions,
        last_execution_id=snapshot.last_execution_id,
        last_tick_at=snapshot.last_tick_at,
        last_error=snapshot.last_error,
        has_last_signal=snapshot.last_signal is not None,
        tracked_symbols=list(snapshot.tracked_symbols),
        idempotency=idempotency,
        state=build_worker_state(runtime_status),
    )
    matching = PersistenceMatchingPayload(
        health=matching_snapshot.health,
        stats=matching_snapshot.stats,
    )

    return PersistenceStatusResult(
        status="ok",
        worker=worker,
        matching=matching,
        stores=stores,
    )


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
