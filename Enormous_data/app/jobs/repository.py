from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.jobs.models import JOB_ACTIVE_STATUSES, JobList, JobRecord


JSON_FIELDS = {"input_snapshot", "quality_report", "output_artifacts", "spark_history_metrics"}


class JobRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_jobs (
                  job_id TEXT PRIMARY KEY,
                  job_type TEXT NOT NULL,
                  status TEXT NOT NULL,
                  config_path TEXT NOT NULL,
                  input_path TEXT,
                  storage_mode TEXT,
                  created_at TEXT NOT NULL,
                  started_at TEXT,
                  finished_at TEXT,
                  elapsed_seconds REAL,
                  message TEXT,
                  error TEXT,
                  stdout TEXT,
                  stderr TEXT,
                  artifact_dir TEXT,
                  run_id TEXT,
                  contract_version TEXT,
                  config_hash TEXT,
                  spark_application_id TEXT,
                  spark_application_status TEXT,
                  spark_history_metrics_status TEXT,
                  spark_history_metrics_error TEXT,
                  spark_history_metrics TEXT,
                  input_snapshot TEXT,
                  quality_status TEXT,
                  quality_report TEXT,
                  output_artifacts TEXT,
                  failure_stage TEXT
                )
                """
            )
            self._migrate_columns(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_created_at ON pipeline_jobs(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status)")

    def create(self, job: JobRecord) -> JobRecord:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_jobs (
                  job_id, job_type, status, config_path, input_path, storage_mode, created_at,
                  started_at, finished_at, elapsed_seconds, message, error, stdout, stderr, artifact_dir,
                  run_id, contract_version, config_hash, spark_application_id,
                  spark_application_status, spark_history_metrics_status,
                  spark_history_metrics_error, spark_history_metrics, input_snapshot,
                  quality_status, quality_report, output_artifacts, failure_stage
                )
                VALUES (
                  :job_id, :job_type, :status, :config_path, :input_path, :storage_mode, :created_at,
                  :started_at, :finished_at, :elapsed_seconds, :message, :error, :stdout, :stderr, :artifact_dir,
                  :run_id, :contract_version, :config_hash, :spark_application_id,
                  :spark_application_status, :spark_history_metrics_status,
                  :spark_history_metrics_error, :spark_history_metrics, :input_snapshot,
                  :quality_status, :quality_report, :output_artifacts, :failure_stage
                )
                """,
                self._serialize(job.to_dict()),
            )
        return job

    def get(self, job_id: str) -> JobRecord | None:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pipeline_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._record(row) if row else None

    def latest(self) -> JobRecord | None:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pipeline_jobs ORDER BY created_at DESC LIMIT 1").fetchone()
        return self._record(row) if row else None

    def active(self) -> JobRecord | None:
        self.initialize()
        placeholders = ",".join("?" for _ in JOB_ACTIVE_STATUSES)
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM pipeline_jobs WHERE status IN ({placeholders}) ORDER BY created_at DESC LIMIT 1",
                tuple(JOB_ACTIVE_STATUSES),
            ).fetchone()
        return self._record(row) if row else None

    def list_recent(self, limit: int = 20) -> JobList:
        self.initialize()
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pipeline_jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM pipeline_jobs").fetchone()[0]
        return JobList(total=total, rows=[self._record(row) for row in rows])

    def update(self, job_id: str, **fields: Any) -> JobRecord:
        self.initialize()
        if not fields:
            job = self.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return job

        assignments = ", ".join(f"{key} = :{key}" for key in fields)
        payload = self._serialize({"job_id": job_id, **fields})
        with self._connect() as conn:
            result = conn.execute(f"UPDATE pipeline_jobs SET {assignments} WHERE job_id = :job_id", payload)
            if result.rowcount == 0:
                raise KeyError(job_id)

        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _migrate_columns(conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(pipeline_jobs)").fetchall()}
        desired = {
            "run_id": "TEXT",
            "contract_version": "TEXT",
            "config_hash": "TEXT",
            "spark_application_id": "TEXT",
            "spark_application_status": "TEXT",
            "spark_history_metrics_status": "TEXT",
            "spark_history_metrics_error": "TEXT",
            "spark_history_metrics": "TEXT",
            "input_snapshot": "TEXT",
            "quality_status": "TEXT",
            "quality_report": "TEXT",
            "output_artifacts": "TEXT",
            "failure_stage": "TEXT",
        }
        for name, column_type in desired.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE pipeline_jobs ADD COLUMN {name} {column_type}")

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        for field in JSON_FIELDS:
            if field in result and result[field] is not None:
                result[field] = json.dumps(result[field], ensure_ascii=False)
        return result

    @staticmethod
    def _deserialize(payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        for field in JSON_FIELDS:
            value = result.get(field)
            if isinstance(value, str) and value:
                result[field] = json.loads(value)
        return result

    @staticmethod
    def _record(row: sqlite3.Row) -> JobRecord:
        return JobRecord(**JobRepository._deserialize(dict(row)))
