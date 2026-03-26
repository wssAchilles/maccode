from __future__ import annotations

from dataclasses import dataclass

from app.matching_service import MatchingService
from app.redis_worker import RedisMarketWorker
from app.signal_service import SignalService
from app.signal_store import SignalStore
from app.summary_service import StrategySummaryService
from app.system_status_service import SystemStatusService


@dataclass(slots=True)
class RuntimeContainer:
    worker: RedisMarketWorker
    signal_store: SignalStore
    signal_service: SignalService
    summary_service: StrategySummaryService
    matching_service: MatchingService
    system_status_service: SystemStatusService


def build_runtime_container(*, started_at: float) -> RuntimeContainer:
    worker = RedisMarketWorker()
    signal_store = SignalStore()
    signal_service = SignalService(
        worker=worker,
        signal_store=signal_store,
    )
    summary_service = StrategySummaryService(
        worker=worker,
        signal_store=signal_store,
    )
    matching_service = MatchingService(worker=worker)
    system_status_service = SystemStatusService(
        worker=worker,
        signal_store=signal_store,
        started_at=started_at,
    )
    return RuntimeContainer(
        worker=worker,
        signal_store=signal_store,
        signal_service=signal_service,
        summary_service=summary_service,
        matching_service=matching_service,
        system_status_service=system_status_service,
    )
