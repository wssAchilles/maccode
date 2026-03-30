from __future__ import annotations

from dataclasses import dataclass

from app.application import (
    InferenceApplicationService,
    OptimizationApplicationService,
    SignalApplicationService,
    SummaryApplicationService,
    SystemStatusApplicationService,
)
from app.config import settings
from app.infrastructure.inference_artifacts import (
    GcsArtifactLoader,
    LoadedInferenceArtifacts,
    PublicGoogleDriveArtifactLoader,
)
from app.infrastructure.inference_runtime import (
    DisabledInferenceEngine,
    MovingAverageInferenceEngine,
    OnnxInferenceEngine,
    StaticModelRegistry,
)
from app.infrastructure.inference_rollout import RuntimeInferenceRolloutManager
from app.infrastructure.inference_rollout_state import RedisInferenceRolloutStateStore
from app.infrastructure.matching_gateway import MatchingGatewayAdapter
from app.infrastructure.persistence_status import WorkerPersistenceStatusAdapter
from app.infrastructure.portfolio_optimizer import GurobiPortfolioOptimizer
from app.infrastructure.signal_runtime import (
    WorkerSignalClaimsAdapter,
    WorkerSignalEventFlowAdapter,
    WorkerSignalRuntimeAdapter,
)
from app.infrastructure.system_status import (
    MatchingObservabilityAdapter,
    SignalStoreStatusAdapter,
    WorkerRuntimeStatusAdapter,
)
from app.inference_service import InferenceService
from app.matching_service import MatchingService
from app.ports import RegisteredModel
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
    inference_service: InferenceService
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
    loaded_artifacts = _load_inference_artifacts()
    inference_registry = _build_inference_registry(loaded_artifacts)
    active_model = inference_registry.active_model()
    inference_rollout = RuntimeInferenceRolloutManager(
        configured_mode=settings.inference_mode,
        active_model=active_model,
        started_at=started_at,
        required_macro_f1=settings.inference_primary_min_macro_f1,
        required_observe_ticks=settings.inference_primary_min_observe_ticks,
        required_agreement_ratio=settings.inference_primary_min_agreement_ratio,
        force_primary=settings.inference_rollout_force_primary,
        max_audit_events=settings.inference_audit_max_events,
        state_store=(
            RedisInferenceRolloutStateStore(
                redis_getter=lambda: worker.redis_client,
                state_key=settings.inference_rollout_state_key,
            )
            if settings.inference_enabled and settings.inference_rollout_state_enabled
            else None
        ),
        persist_every_observations=settings.inference_rollout_persist_every_observations,
    )
    if settings.inference_enabled and active_model is not None:
        if loaded_artifacts is not None:
            inference_engine = OnnxInferenceEngine(
                engine_name=active_model.metadata.get("engine_name", settings.inference_engine_name),
                mode=settings.inference_mode,
                model=active_model,
                artifacts=loaded_artifacts,
            )
        else:
            inference_engine = MovingAverageInferenceEngine(
                engine_name=settings.inference_engine_name,
                mode=settings.inference_mode,
                model=active_model,
                fast_window=settings.fast_window,
                slow_window=settings.slow_window,
            )
    else:
        inference_engine = DisabledInferenceEngine()
    inference_application = InferenceApplicationService(
        engine=inference_engine,
        model_registry=inference_registry,
        rollout=inference_rollout,
    )
    signal_application = SignalApplicationService(
        runtime=signal_runtime,
        signal_store=signal_store,
        signal_claims=WorkerSignalClaimsAdapter(worker),
        event_flow=WorkerSignalEventFlowAdapter(worker),
        publishers=(worker.firebase_publisher, worker.supabase_publisher),
        inference_engine=inference_engine,
        inference_mode=settings.inference_mode,
        inference_rollout=inference_rollout,
    )
    worker.attach_signal_application(signal_application)
    system_status_application = SystemStatusApplicationService(
        runtime_status=runtime_status,
        signal_store_status=signal_store_status,
        matching_observability=matching_observability,
        started_at=started_at,
    )
    summary_application = SummaryApplicationService(
        inference_application=inference_application,
        signal_runtime=signal_runtime,
        signal_store=signal_store,
        matching_gateway=matching_gateway,
        persistence_status=WorkerPersistenceStatusAdapter(system_status_application),
    )
    signal_service = SignalService(
        application=signal_application,
    )
    inference_service = InferenceService(
        application=inference_application,
    )
    optimization_service = OptimizationApplicationService(
        optimizer=GurobiPortfolioOptimizer(),
    )
    summary_service = StrategySummaryService(
        application=summary_application,
    )
    matching_service = MatchingService(gateway=matching_gateway)
    system_status_service = SystemStatusService(
        application=system_status_application,
    )
    return RuntimeContainer(
        worker=worker,
        signal_store=signal_store,
        signal_service=signal_service,
        inference_service=inference_service,
        optimization_service=optimization_service,
        summary_service=summary_service,
        matching_service=matching_service,
        system_status_service=system_status_service,
    )


def _load_inference_artifacts() -> LoadedInferenceArtifacts | None:
    if not settings.inference_enabled:
        return None
    if settings.inference_model_source == "google_drive":
        loader = PublicGoogleDriveArtifactLoader(
            folder_url=settings.inference_artifact_folder_url,
            cache_dir=settings.inference_artifact_cache_dir,
        )
    elif settings.inference_model_source == "gcs":
        loader = GcsArtifactLoader(
            gcs_uri=settings.inference_artifact_gcs_uri,
            cache_dir=settings.inference_artifact_cache_dir,
        )
    else:
        return None
    return loader.load()


def _build_inference_registry(loaded_artifacts: LoadedInferenceArtifacts | None) -> StaticModelRegistry:
    if not settings.inference_enabled:
        return StaticModelRegistry(models=())
    if loaded_artifacts is not None:
        manifest = loaded_artifacts.manifest
        model = RegisteredModel(
            model_id=str(manifest.get("model_id", settings.inference_model_id)),
            version=str(manifest.get("model_version", settings.inference_model_version)),
            source=str(manifest.get("model_source", settings.inference_model_source)),
            task=str(manifest.get("task", "signal_inference")),
            symbols=tuple(str(item) for item in manifest.get("symbols", [])),
            metadata={
                "engine_name": str(manifest.get("engine_name", settings.inference_engine_name)),
                "lookback": int(manifest.get("lookback", 0)),
                "horizon": int(manifest.get("horizon", 0)),
                "feature_columns": list(manifest.get("feature_columns", [])),
                "feature_count": len(manifest.get("feature_columns", [])),
                "best_macro_f1": float(loaded_artifacts.metrics.get("best_macro_f1", 0.0)),
                "artifact_cache_dir": str(loaded_artifacts.cache_dir),
            },
        )
        return StaticModelRegistry(models=(model,), active_model_id=model.model_id)
    symbols = tuple(
        item.strip()
        for item in settings.inference_model_symbols.split(",")
        if item.strip()
    )
    model = RegisteredModel(
        model_id=settings.inference_model_id,
        version=settings.inference_model_version,
        source=settings.inference_model_source,
        symbols=symbols,
        metadata={
            "fast_window": settings.fast_window,
            "slow_window": settings.slow_window,
        },
    )
    return StaticModelRegistry(
        models=(model,),
        active_model_id=model.model_id,
    )
