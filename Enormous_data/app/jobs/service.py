from __future__ import annotations

import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml

from app.jobs.models import JobRecord
from app.jobs.repository import JobRepository
from app.pipeline.runner import SparkPipelineRunner
from app.services.spark_runner import SparkJobRunningError
from scripts.collect_spark_history_metrics import collect_metrics as collect_spark_history_metrics
from spark_jobs.writers import write_json_atomic


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobNotFoundError(RuntimeError):
    pass


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        runner: SparkPipelineRunner,
        project_root: str | Path,
        config_path: str | Path,
        cache_dir: str | Path,
    ):
        self.repository = repository
        self.runner = runner
        self.project_root = Path(project_root)
        self.config_path = Path(config_path)
        self.cache_dir = Path(cache_dir)

    def enqueue_refresh(self) -> JobRecord:
        active = self.repository.active()
        if active:
            raise SparkJobRunningError(f"spark refresh job is already {active.status}: {active.job_id}")

        config = self._load_pipeline_config()
        data_config = config.get("data", {})
        storage_config = config.get("storage", {})
        job_id = uuid4().hex
        job = self.repository.create(
            JobRecord(
                job_id=job_id,
                job_type="spark_refresh",
                status="queued",
                config_path=str(self.config_path),
                input_path=data_config.get("input_path"),
                storage_mode=storage_config.get("mode", "local"),
                created_at=utc_now(),
                message="spark refresh queued",
                run_id=job_id,
            )
        )
        self._write_current_job(job)
        thread = threading.Thread(target=self._run_job, args=(job.job_id,), daemon=True)
        thread.start()
        return job

    def latest_job(self) -> JobRecord | None:
        return self.repository.latest()

    def list_jobs(self, limit: int = 20):
        return self.repository.list_recent(limit)

    def get_job(self, job_id: str) -> JobRecord:
        job = self.repository.get(job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        return job

    def _run_job(self, job_id: str) -> None:
        started_at = utc_now()
        self.repository.update(job_id, status="running", started_at=started_at, message="spark refresh started")
        self._write_current_job(self.get_job(job_id))

        current = self.get_job(job_id)
        result = self.runner.run(self.config_path, run_id=current.run_id or job_id)
        finished_at = utc_now()
        governance_fields = self._governance_fields(result.manifest)
        governance_fields.update(self._spark_history_fields(result.manifest))
        if result.succeeded:
            job = self.repository.update(
                job_id,
                status="succeeded",
                finished_at=finished_at,
                elapsed_seconds=result.elapsed_seconds,
                message=result.stdout or "spark refresh finished",
                stdout=result.stdout,
                stderr=result.stderr,
                **governance_fields,
            )
        else:
            failed_status = "rejected" if governance_fields.get("failure_stage") == "quality_gate" else "failed"
            job = self.repository.update(
                job_id,
                status=failed_status,
                finished_at=finished_at,
                elapsed_seconds=result.elapsed_seconds,
                message=result.stderr or "spark refresh failed",
                error=result.stderr or result.stdout or "spark refresh failed",
                stdout=result.stdout,
                stderr=result.stderr,
                **governance_fields,
            )
        self._write_current_job(job)

    @staticmethod
    def _governance_fields(manifest: dict[str, object] | None) -> dict[str, object]:
        if not manifest:
            return {}
        return {
            "run_id": manifest.get("run_id"),
            "contract_version": manifest.get("contract_version"),
            "config_hash": manifest.get("config_hash"),
            "spark_application_id": manifest.get("spark_application_id"),
            "spark_application_status": manifest.get("spark_application_status"),
            "input_snapshot": manifest.get("input_snapshot"),
            "quality_status": manifest.get("quality_status"),
            "quality_report": manifest.get("quality_report"),
            "output_artifacts": manifest.get("output_artifacts"),
            "failure_stage": manifest.get("failure_stage"),
        }

    @staticmethod
    def _spark_history_fields(manifest: dict[str, object] | None) -> dict[str, object]:
        base = {
            "spark_history_metrics_status": "not_configured",
            "spark_history_metrics_error": None,
            "spark_history_metrics": None,
        }
        if not manifest:
            return base

        history_url = os.getenv("SPARK_HISTORY_URL", "").strip()
        app_id = str(manifest.get("spark_application_id") or "").strip()
        if not history_url or not app_id:
            return base

        attempts = max(1, int(os.getenv("SPARK_HISTORY_RETRY_ATTEMPTS", "4")))
        delay_seconds = max(0.0, float(os.getenv("SPARK_HISTORY_RETRY_SECONDS", "2")))
        last_error = ""
        for attempt in range(attempts):
            try:
                metrics = collect_spark_history_metrics(history_url, app_id)
                return {
                    **base,
                    "spark_history_metrics_status": "collected",
                    "spark_history_metrics_error": "",
                    "spark_history_metrics": metrics,
                }
            except Exception as exc:
                last_error = str(exc)
                if attempt < attempts - 1 and delay_seconds:
                    time.sleep(delay_seconds)

        return {
            **base,
            "spark_history_metrics_status": "unavailable",
            "spark_history_metrics_error": last_error,
        }

    def _load_pipeline_config(self) -> dict[str, object]:
        path = self.config_path
        if not path.is_absolute():
            path = self.project_root / path
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _write_current_job(self, job: JobRecord) -> None:
        payload = job.to_dict()
        payload["status"] = "success" if job.status == "succeeded" else job.status
        write_json_atomic(self.cache_dir / "job.json", payload)
