"""Routing and budget guardrails for ml_train execution backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from google.cloud import firestore

from config import Config
from services.storage_service import StorageService


@dataclass(frozen=True)
class MlTrainRoutingDecision:
    backend: str
    reason: str
    dataset_size_bytes: int
    rollout_allowed: bool
    budget_guard: Dict[str, Any]


class MlTrainBackendSelector:
    """Choose between legacy Cloud Run training and Vertex AI training."""

    @classmethod
    def decide(
        cls,
        uid: str,
        payload: Dict[str, Any],
    ) -> MlTrainRoutingDecision:
        requested_backend = str(payload.get('training_backend') or '').strip().lower()
        dataset_size_bytes = cls._dataset_size_bytes(payload.get('storage_path'))
        rollout_allowed = cls._rollout_allowed(uid)
        budget_guard = cls._build_budget_guard(dataset_size_bytes)
        default_backend = Config.ML_TRAIN_BACKEND_DEFAULT

        if requested_backend in {'cloud_run_legacy', 'vertex_custom_training'}:
            selected = requested_backend
        else:
            size_prefers_vertex = (
                dataset_size_bytes >= Config.ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES
            )
            selected = (
                'vertex_custom_training'
                if default_backend == 'vertex_custom_training' or size_prefers_vertex
                else 'cloud_run_legacy'
            )

        vertex_ready = (
            Config.ML_TRAIN_VERTEX_ENABLED
            and bool(Config.VERTEX_TRAINING_IMAGE_URI)
            and bool(Config.TRAINING_CALLBACK_BASE_URL)
        )
        if selected == 'vertex_custom_training' and not vertex_ready:
            return MlTrainRoutingDecision(
                backend='cloud_run_legacy',
                reason='Vertex training is not fully configured',
                dataset_size_bytes=dataset_size_bytes,
                rollout_allowed=rollout_allowed,
                budget_guard=budget_guard,
            )

        if selected == 'vertex_custom_training' and not rollout_allowed:
            return MlTrainRoutingDecision(
                backend='cloud_run_legacy',
                reason='Vertex rollout gate keeps this user on legacy backend',
                dataset_size_bytes=dataset_size_bytes,
                rollout_allowed=False,
                budget_guard=budget_guard,
            )

        if selected == 'vertex_custom_training':
            active_jobs = cls._count_active_vertex_jobs()
            budget_guard['active_parallel_jobs'] = active_jobs
            if active_jobs >= Config.ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS:
                budget_guard['reject_reason'] = (
                    f'Active Vertex training jobs {active_jobs} reached the '
                    f'guardrail limit {Config.ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS}'
                )
                return MlTrainRoutingDecision(
                    backend='rejected',
                    reason=budget_guard['reject_reason'],
                    dataset_size_bytes=dataset_size_bytes,
                    rollout_allowed=rollout_allowed,
                    budget_guard=budget_guard,
                )

        return MlTrainRoutingDecision(
            backend=selected,
            reason='vertex selected by rollout and cost policy'
            if selected == 'vertex_custom_training'
            else 'legacy backend retained by rollout policy',
            dataset_size_bytes=dataset_size_bytes,
            rollout_allowed=rollout_allowed,
            budget_guard=budget_guard,
        )

    @staticmethod
    def _build_budget_guard(dataset_size_bytes: int) -> Dict[str, Any]:
        return {
            'max_runtime_s': Config.ML_TRAIN_VERTEX_MAX_RUNTIME_S,
            'max_parallel_jobs': Config.ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS,
            'cpu_only': Config.ML_TRAIN_VERTEX_CPU_ONLY,
            'dataset_size_bytes': dataset_size_bytes,
        }

    @staticmethod
    def _rollout_allowed(uid: str) -> bool:
        mode = Config.ML_TRAIN_VERTEX_ROLLOUT_MODE
        if mode == 'disabled':
            return False
        if mode == 'manual_all':
            return True
        if mode == 'whitelist':
            return uid in set(Config.ML_TRAIN_VERTEX_WHITELIST_UIDS)
        return False

    @staticmethod
    def _dataset_size_bytes(storage_path: Any) -> int:
        try:
            if not storage_path:
                return 0
            metadata = StorageService().get_file_metadata(str(storage_path))
            return int(metadata.get('size') or 0)
        except Exception:
            return 0

    @staticmethod
    def _iter_operation_records() -> Iterable[Dict[str, Any]]:
        client = firestore.Client(database=Config.FIRESTORE_DATABASE)
        for snapshot in client.collection(Config.JOBS_COLLECTION).stream():
            data = snapshot.to_dict() or {}
            if data:
                yield data

    @classmethod
    def _count_active_vertex_jobs(cls) -> int:
        total = 0
        for record in cls._iter_operation_records():
            if str(record.get('type') or '') != 'ml_train':
                continue
            if str(record.get('status') or '') not in {
                'queued',
                'dispatching',
                'running',
                'retrying',
            }:
                continue
            metadata = record.get('metadata') if isinstance(record.get('metadata'), dict) else {}
            if str(metadata.get('training_backend') or '') != 'vertex_custom_training':
                continue
            total += 1
        return total
