from __future__ import annotations

from services.ml_train_backend_selector import MlTrainBackendSelector


def test_selector_rejects_when_vertex_parallel_guardrail_is_reached(monkeypatch):
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_BACKEND_DEFAULT',
        'vertex_custom_training',
    )
    monkeypatch.setattr('services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_ENABLED', True)
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.VERTEX_TRAINING_IMAGE_URI',
        'us-central1-docker.pkg.dev/data-science-44398/sentinel-jobs/vertex-trainer:latest',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.TRAINING_CALLBACK_BASE_URL',
        'https://data-science-44398.an.r.appspot.com',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_ROLLOUT_MODE',
        'manual_all',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS',
        1,
    )
    monkeypatch.setattr(
        MlTrainBackendSelector,
        '_dataset_size_bytes',
        staticmethod(lambda _path: 1024),
    )
    monkeypatch.setattr(
        MlTrainBackendSelector,
        '_iter_operation_records',
        staticmethod(
            lambda: iter(
                [
                    {
                        'type': 'ml_train',
                        'status': 'running',
                        'metadata': {'training_backend': 'vertex_custom_training'},
                    }
                ]
            )
        ),
    )

    decision = MlTrainBackendSelector.decide('user-1', {'storage_path': 'uploads/train.csv'})

    assert decision.backend == 'rejected'
    assert decision.budget_guard['active_parallel_jobs'] == 1
    assert 'reject_reason' in decision.budget_guard


def test_selector_keeps_legacy_backend_when_rollout_disallows_vertex(monkeypatch):
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_BACKEND_DEFAULT',
        'vertex_custom_training',
    )
    monkeypatch.setattr('services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_ENABLED', True)
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.VERTEX_TRAINING_IMAGE_URI',
        'us-central1-docker.pkg.dev/data-science-44398/sentinel-jobs/vertex-trainer:latest',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.TRAINING_CALLBACK_BASE_URL',
        'https://data-science-44398.an.r.appspot.com',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_ROLLOUT_MODE',
        'whitelist',
    )
    monkeypatch.setattr(
        'services.ml_train_backend_selector.Config.ML_TRAIN_VERTEX_WHITELIST_UIDS',
        ['allowed-user'],
    )
    monkeypatch.setattr(
        MlTrainBackendSelector,
        '_dataset_size_bytes',
        staticmethod(lambda _path: 1024),
    )

    decision = MlTrainBackendSelector.decide('blocked-user', {'storage_path': 'uploads/train.csv'})

    assert decision.backend == 'cloud_run_legacy'
    assert decision.rollout_allowed is False
    assert 'rollout gate' in decision.reason
