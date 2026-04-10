"""Vertex AI Custom Training submission and inspection helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from config import Config


class VertexTrainingService:
    """Thin wrapper around Vertex AI CustomJob APIs."""

    @staticmethod
    def _staging_bucket() -> Optional[str]:
        bucket = str(Config.VERTEX_TRAINING_STAGING_BUCKET or '').strip()
        if not bucket:
            return None
        if bucket.startswith('gs://'):
            return bucket
        return f'gs://{bucket}'

    @staticmethod
    def _sanitize_label(value: str) -> str:
        normalized = re.sub(r'[^a-z0-9_-]+', '-', value.lower())
        return normalized.strip('-_')[:63] or 'na'

    @classmethod
    def submit_custom_job(
        cls,
        *,
        operation_id: str,
        uid: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        from google.cloud import aiplatform

        aiplatform.init(
            project=Config.GCP_PROJECT_ID,
            location=Config.VERTEX_REGION,
            staging_bucket=cls._staging_bucket(),
        )

        display_name = (
            f"ml-train-{cls._sanitize_label(uid)[:18]}-"
            f"{cls._sanitize_label(operation_id)[:24]}"
        )[:120]
        env = [
            {'name': 'TRAINING_UID', 'value': uid},
            {'name': 'TRAINING_OPERATION_ID', 'value': operation_id},
            {'name': 'TRAINING_STORAGE_PATH', 'value': str(payload.get('storage_path') or '')},
            {'name': 'TRAINING_MODEL_TYPE', 'value': str(payload.get('model_type') or 'lstm')},
            {'name': 'TRAINING_TARGET_COLUMN', 'value': str(payload.get('target_column') or '')},
            {'name': 'TRAINING_WINDOW_SIZE', 'value': str(payload.get('window_size', payload.get('lookback', 24)))},
            {'name': 'TRAINING_HORIZON', 'value': str(payload.get('horizon', 1))},
            {'name': 'TRAINING_EPOCHS', 'value': str(payload.get('epochs', 10))},
            {'name': 'TRAINING_BATCH_SIZE', 'value': str(payload.get('batch_size', 32))},
            {'name': 'GCP_PROJECT_ID', 'value': Config.GCP_PROJECT_ID},
            {'name': 'STORAGE_BUCKET_NAME', 'value': Config.STORAGE_BUCKET_NAME},
            {'name': 'TRAINING_CALLBACK_BASE_URL', 'value': Config.TRAINING_CALLBACK_BASE_URL},
            {'name': 'TRAINING_CALLBACK_TOKEN', 'value': Config.INTERNAL_JOB_TOKEN},
            {'name': 'VERTEX_JOB_REGION', 'value': Config.VERTEX_REGION},
        ]
        machine_spec: Dict[str, Any] = {
            'machine_type': Config.VERTEX_TRAINING_MACHINE_TYPE,
        }
        if (
            not Config.ML_TRAIN_VERTEX_CPU_ONLY
            and Config.VERTEX_TRAINING_ACCELERATOR_TYPE
            and Config.VERTEX_TRAINING_ACCELERATOR_COUNT > 0
        ):
            machine_spec['accelerator_type'] = Config.VERTEX_TRAINING_ACCELERATOR_TYPE
            machine_spec['accelerator_count'] = Config.VERTEX_TRAINING_ACCELERATOR_COUNT

        custom_job = aiplatform.CustomJob(
            display_name=display_name,
            worker_pool_specs=[
                {
                    'machine_spec': machine_spec,
                    'replica_count': 1,
                    'container_spec': {
                        'image_uri': Config.VERTEX_TRAINING_IMAGE_URI,
                        'env': env,
                    },
                }
            ],
            labels={
                'job_type': 'ml_train',
                'backend': 'vertex',
                'operation': cls._sanitize_label(operation_id)[:63],
            },
            staging_bucket=cls._staging_bucket(),
        )
        custom_job.submit(
            service_account=Config.VERTEX_TRAINING_SERVICE_ACCOUNT or None,
            timeout=Config.ML_TRAIN_VERTEX_MAX_RUNTIME_S,
            create_request_timeout=60.0,
            disable_retries=True,
        )
        custom_job.wait_for_resource_creation()
        return cls.build_external_job_metadata(
            job_name=str(custom_job.resource_name),
            display_name=display_name,
            state='JOB_STATE_PENDING',
            started_at=None,
            ended_at=None,
        )

    @classmethod
    def get_custom_job(cls, job_name: str):
        from google.cloud.aiplatform_v1 import JobServiceClient

        client = JobServiceClient(
            client_options={'api_endpoint': f'{Config.VERTEX_REGION}-aiplatform.googleapis.com'}
        )
        return client.get_custom_job(name=job_name)

    @classmethod
    def get_job_snapshot(cls, job_name: str) -> Dict[str, Any]:
        from google.protobuf.json_format import MessageToDict

        job = cls.get_custom_job(job_name)
        state = getattr(job.state, 'name', str(job.state))
        started_at = cls._timestamp_to_iso(getattr(job, 'start_time', None))
        ended_at = cls._timestamp_to_iso(getattr(job, 'end_time', None))
        error = None
        if getattr(job, 'error', None):
            error = MessageToDict(job.error._pb)  # type: ignore[attr-defined]
        return {
            **cls.build_external_job_metadata(
                job_name=job.name,
                display_name=job.display_name,
                state=state,
                started_at=started_at,
                ended_at=ended_at,
            ),
            'create_time': cls._timestamp_to_iso(getattr(job, 'create_time', None)),
            'update_time': cls._timestamp_to_iso(getattr(job, 'update_time', None)),
            'error': error,
            'web_access_uris': dict(getattr(job, 'web_access_uris', {}) or {}),
        }

    @classmethod
    def cancel_custom_job(cls, job_name: str) -> None:
        from google.cloud.aiplatform_v1 import JobServiceClient

        client = JobServiceClient(
            client_options={'api_endpoint': f'{Config.VERTEX_REGION}-aiplatform.googleapis.com'}
        )
        client.cancel_custom_job(name=job_name)

    @classmethod
    def build_external_job_metadata(
        cls,
        *,
        job_name: str,
        display_name: str,
        state: str,
        started_at: Optional[str],
        ended_at: Optional[str],
    ) -> Dict[str, Any]:
        return {
            'provider': 'vertex_ai',
            'name': job_name,
            'display_name': display_name,
            'region': Config.VERTEX_REGION,
            'state': state,
            'console_url': cls.console_url(job_name),
            'machine_type': Config.VERTEX_TRAINING_MACHINE_TYPE,
            'accelerator_type': Config.VERTEX_TRAINING_ACCELERATOR_TYPE or None,
            'accelerator_count': Config.VERTEX_TRAINING_ACCELERATOR_COUNT,
            'started_at': started_at,
            'ended_at': ended_at,
        }

    @classmethod
    def console_url(cls, job_name: str) -> str:
        job_id = str(job_name).rsplit('/', 1)[-1]
        return (
            f'https://console.cloud.google.com/vertex-ai/locations/'
            f'{Config.VERTEX_REGION}/training/{job_id}'
            f'?project={Config.GCP_PROJECT_ID}'
        )

    @staticmethod
    def _timestamp_to_iso(value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            seconds = int(getattr(value, 'seconds', 0) or 0)
            nanos = int(getattr(value, 'nanos', 0) or 0)
            if seconds == 0 and nanos == 0:
                return None
            from datetime import datetime, timezone

            return datetime.fromtimestamp(
                seconds + (nanos / 1_000_000_000),
                tz=timezone.utc,
            ).isoformat()
        except Exception:
            return None
