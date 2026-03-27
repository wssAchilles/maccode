from __future__ import annotations

from dataclasses import dataclass

from app.application import (
    OptimizationApplicationService,
    SignalApplicationService,
    SummaryApplicationService,
)
from app.infrastructure import (
    GurobiPortfolioOptimizer,
    MatchingObservabilityAdapter,
    MatchingGatewayAdapter,
    SignalStoreStatusAdapter,
    WorkerPersistenceStatusAdapter,
    WorkerRuntimeStatusAdapter,
    WorkerSignalClaimsAdapter,
    WorkerSignalEventFlowAdapter,
    WorkerSignalRuntimeAdapter,
)
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
    optimization_service: OptimizationApplicationService
    summary_service: StrategySummaryService
    matching_service: MatchingService
    system_status_service: SystemStatusService


def build_runtime_container(*, started_at: float) -> RuntimeContainer:
    worker = RedisMarketWorker()
    signal_store = SignalStore()
    signal_runtime = WorkerSignalRuntimeAdapter(worker)
    runtime_status = WorkerRuntimeStatusAdapter(worker)
    signal_store_status = SignalStoreStatusAdapter(signal_store)
    matching_gateway = MatchingGatewayAdapter(worker.matching_client)
    matching_observability = MatchingObservabilityAdapter(matching_gateway)
    signal_application = SignalApplicationService(
        runtime=signal_runtime,
        signal_store=signal_store,
        signal_claims=WorkerSignalClaimsAdapter(worker),
        event_flow=WorkerSignalEventFlowAdapter(worker),
        publishers=(worker.firebase_publisher, worker.supabase_publisher),
    )
    worker.attach_signal_application(signal_application)
    summary_application = SummaryApplicationService(
        signal_runtime=signal_runtime,
        signal_store=signal_store,
        matching_gateway=matching_gateway,
        persistence_status=WorkerPersistenceStatusAdapter(
            runtime_status,
            signal_store_status,
            matching_observability,
        ),
    )
    signal_service = SignalService(
        application=signal_application,
    )
    optimization_service = OptimizationApplicationService(
        optimizer=GurobiPortfolioOptimizer(),
    )
    summary_service = StrategySummaryService(
        application=summary_application,
    )
    matching_service = MatchingService(gateway=matching_gateway)
    system_status_service = SystemStatusService(
        runtime_status=runtime_status,
        signal_store_status=signal_store_status,
        matching_observability=matching_observability,
        started_at=started_at,
    )
    return RuntimeContainer(
        worker=worker,
        signal_store=signal_store,
        signal_service=signal_service,
        optimization_service=optimization_service,
        summary_service=summary_service,
        matching_service=matching_service,
        system_status_service=system_status_service,
    )
