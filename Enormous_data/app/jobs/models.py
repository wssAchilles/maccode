from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


JOB_TERMINAL_STATUSES = {"succeeded", "failed", "rejected"}
JOB_ACTIVE_STATUSES = {"queued", "running"}


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    job_type: str
    status: str
    config_path: str
    input_path: str | None
    storage_mode: str | None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_seconds: float | None = None
    message: str | None = None
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    artifact_dir: str | None = None
    run_id: str | None = None
    contract_version: str | None = None
    config_hash: str | None = None
    spark_application_id: str | None = None
    spark_application_status: str | None = None
    spark_history_metrics_status: str | None = None
    spark_history_metrics_error: str | None = None
    spark_history_metrics: dict[str, Any] | None = None
    input_snapshot: dict[str, Any] | None = None
    quality_status: str | None = None
    quality_report: dict[str, Any] | None = None
    output_artifacts: dict[str, Any] | None = None
    failure_stage: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class JobList:
    total: int
    rows: list[JobRecord]

    def to_dict(self) -> dict[str, object]:
        return {"total": self.total, "rows": [job.to_dict() for job in self.rows]}
