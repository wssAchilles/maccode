from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.jobs.models import JobRecord


GOVERNANCE_CONTRACT_VERSION = "job-governance/v1"
FRESHNESS_WARN_MINUTES = 12 * 60
FRESHNESS_FAIL_MINUTES = 24 * 60


ARTIFACT_SPECS = [
    ("run_manifest", ("run_manifest_path",), "manifest"),
    ("dashboard_cube_summary", ("dashboard_cube_artifacts", "summary"), "dashboard_cube"),
    ("dashboard_cube_semantics", ("dashboard_cube_artifacts", "semantic_metrics"), "dashboard_cube"),
    ("dashboard_cube_total", ("dashboard_cube_artifacts", "total"), "dashboard_cube"),
    ("dashboard_cube_daily", ("dashboard_cube_artifacts", "daily"), "dashboard_cube"),
    ("feature_mart_summary", ("feature_mart_artifacts", "summary"), "feature_mart"),
    ("feature_mart_freshness", ("feature_mart_artifacts", "freshness"), "feature_mart"),
    ("recommendation_evaluation", ("recommendation_artifacts", "evaluation"), "algorithm"),
    ("forecasting_evaluation", ("forecasting_artifacts", "evaluation"), "algorithm"),
    ("anomaly_incidents", ("anomaly_artifacts", "incidents"), "algorithm"),
    ("optimization_plan", ("optimization_artifacts", "plan"), "algorithm"),
]


def build_job_governance(job: JobRecord, project_root: str | Path, cache_dir: str | Path) -> dict[str, Any]:
    artifacts = _build_artifacts(job, Path(project_root), Path(cache_dir))
    stages = _build_stages(job, artifacts)
    artifact_counts = _count_by_status(artifacts)
    stage_counts = _count_by_status(stages)
    return {
        "contract_version": GOVERNANCE_CONTRACT_VERSION,
        "run_id": job.run_id or job.job_id,
        "status": _publish_status(job, artifact_counts),
        "active_stage": _active_stage(stages),
        "completion_ratio": _completion_ratio(stages),
        "freshness_sla_minutes": FRESHNESS_FAIL_MINUTES,
        "freshness_warning_minutes": FRESHNESS_WARN_MINUTES,
        "stage_counts": stage_counts,
        "artifact_counts": artifact_counts,
        "stages": stages,
        "artifacts": artifacts,
        "spark_summary": _spark_summary(job),
        "quality_summary": _quality_summary(job),
    }


def job_with_governance(job: JobRecord, project_root: str | Path, cache_dir: str | Path) -> dict[str, Any]:
    payload = job.to_dict()
    payload["governance"] = build_job_governance(job, project_root=project_root, cache_dir=cache_dir)
    return payload


def _build_stages(job: JobRecord, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "stage": "queued",
            "status": "succeeded" if job.started_at or job.status in {"running", "succeeded", "failed", "rejected"} else "running",
            "started_at": job.created_at,
            "finished_at": job.started_at,
            "duration_seconds": _seconds_between(job.created_at, job.started_at),
        },
        {
            "stage": "spark_execution",
            "status": _spark_stage_status(job),
            "started_at": job.started_at,
            "finished_at": job.finished_at if job.status in {"succeeded", "failed", "rejected"} else None,
            "duration_seconds": job.elapsed_seconds,
        },
        {
            "stage": "history_metrics",
            "status": _history_stage_status(job),
            "started_at": job.finished_at,
            "finished_at": job.finished_at if job.spark_history_metrics_status else None,
            "duration_seconds": None,
        },
        {
            "stage": "quality_gate",
            "status": _quality_stage_status(job),
            "started_at": job.finished_at,
            "finished_at": job.finished_at if job.quality_status else None,
            "duration_seconds": None,
        },
        {
            "stage": "artifact_publish",
            "status": _artifact_stage_status(job, artifacts),
            "started_at": job.finished_at,
            "finished_at": job.finished_at if job.output_artifacts else None,
            "duration_seconds": None,
        },
    ]


def _spark_stage_status(job: JobRecord) -> str:
    if job.status == "queued":
        return "pending"
    if job.status == "running":
        return "running"
    if job.status == "succeeded":
        return "succeeded"
    if job.status in {"failed", "rejected"}:
        return "failed"
    return "pending"


def _history_stage_status(job: JobRecord) -> str:
    if job.status in {"queued", "running"}:
        return "pending"
    status = job.spark_history_metrics_status
    if status == "collected":
        return "succeeded"
    if status == "unavailable":
        return "warning"
    if status == "not_configured":
        return "skipped"
    if job.status in {"failed", "rejected"}:
        return "skipped"
    return "pending"


def _quality_stage_status(job: JobRecord) -> str:
    if job.status in {"queued", "running"}:
        return "pending"
    if job.quality_status == "passed":
        return "succeeded"
    if job.quality_status == "failed":
        return "failed"
    if job.quality_status == "needs_review":
        return "warning"
    if job.status in {"failed", "rejected"}:
        return "skipped"
    return "pending"


def _artifact_stage_status(job: JobRecord, artifacts: list[dict[str, Any]]) -> str:
    if job.status in {"queued", "running"}:
        return "pending"
    if job.status in {"failed", "rejected"}:
        return "skipped"
    if not artifacts:
        return "warning"
    missing_count = sum(1 for artifact in artifacts if artifact["status"] == "missing")
    if missing_count == 0:
        return "succeeded"
    if missing_count < len(artifacts):
        return "warning"
    return "failed"


def _build_artifacts(job: JobRecord, project_root: Path, cache_dir: Path) -> list[dict[str, Any]]:
    output_artifacts = job.output_artifacts or {}
    rows: list[dict[str, Any]] = []
    for artifact_id, path_keys, artifact_type in ARTIFACT_SPECS:
        raw_path = _nested_value(output_artifacts, path_keys)
        if not raw_path and len(path_keys) == 1:
            raw_path = output_artifacts.get(path_keys[0])
        if not raw_path:
            continue
        artifact_path = _resolve_path(str(raw_path), project_root, cache_dir)
        stat_payload = _artifact_stat(artifact_path)
        rows.append(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "path": str(raw_path),
                "exists": stat_payload["exists"],
                "status": stat_payload["status"],
                "updated_at": stat_payload["updated_at"],
                "age_minutes": stat_payload["age_minutes"],
                "size_bytes": stat_payload["size_bytes"],
                "freshness_sla_minutes": FRESHNESS_FAIL_MINUTES,
                "freshness_warning_minutes": FRESHNESS_WARN_MINUTES,
            }
        )
    return rows


def _nested_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _resolve_path(raw_path: str, project_root: Path, cache_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    direct = project_root / path
    if direct.exists():
        return direct
    if raw_path.startswith("data/cache/"):
        return cache_dir / raw_path.removeprefix("data/cache/")
    return direct


def _artifact_stat(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "status": "missing", "updated_at": None, "age_minutes": None, "size_bytes": None}
    updated = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    age_minutes = max(0.0, (datetime.now(timezone.utc) - updated).total_seconds() / 60)
    if age_minutes <= FRESHNESS_WARN_MINUTES:
        status = "fresh"
    elif age_minutes <= FRESHNESS_FAIL_MINUTES:
        status = "warning"
    else:
        status = "stale"
    return {
        "exists": True,
        "status": status,
        "updated_at": updated.isoformat(),
        "age_minutes": round(age_minutes, 1),
        "size_bytes": _path_size(path),
    }


def _path_size(path: Path) -> int | None:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return None
    total = 0
    for index, child in enumerate(path.iterdir()):
        if index >= 200:
            return None
        if child.is_file():
            total += child.stat().st_size
    return total


def _spark_summary(job: JobRecord) -> dict[str, Any]:
    metrics = job.spark_history_metrics or {}
    return {
        "application_id": job.spark_application_id or metrics.get("spark_application_id"),
        "application_status": job.spark_application_status or metrics.get("spark_application_status"),
        "history_metrics_status": job.spark_history_metrics_status,
        "failed_task_count": _number(metrics.get("failed_task_count")),
        "retried_task_count": _number(metrics.get("retried_task_count")),
        "executor_count": _number(metrics.get("executor_count")),
        "memory_spill_bytes": _number(metrics.get("memory_spill_bytes")),
        "disk_spill_bytes": _number(metrics.get("disk_spill_bytes")),
        "shuffle_read_bytes": _number(metrics.get("shuffle_read_bytes")),
        "shuffle_write_bytes": _number(metrics.get("shuffle_write_bytes")),
        "driver_peak_memory_mb": _number(metrics.get("driver_peak_memory_mb")),
    }


def _quality_summary(job: JobRecord) -> dict[str, Any]:
    gate = ((job.quality_report or {}).get("gate") or {}) if isinstance(job.quality_report, dict) else {}
    checks = gate.get("checks") or []
    return {
        "status": job.quality_status or gate.get("status"),
        "check_count": len(checks),
        "passed_check_count": sum(1 for check in checks if check.get("passed")),
        "failure_stage": job.failure_stage or "none",
    }


def _publish_status(job: JobRecord, artifact_counts: dict[str, int]) -> str:
    if job.status in {"queued", "running"}:
        return job.status
    if job.status in {"failed", "rejected"}:
        return job.status
    if artifact_counts.get("missing", 0) > 0 or artifact_counts.get("stale", 0) > 0:
        return "degraded"
    if artifact_counts.get("warning", 0) > 0:
        return "warning"
    return "published"


def _active_stage(stages: list[dict[str, Any]]) -> str:
    for stage in stages:
        if stage["status"] in {"running", "pending", "warning", "failed"}:
            return stage["stage"]
    return stages[-1]["stage"] if stages else "unknown"


def _completion_ratio(stages: list[dict[str, Any]]) -> float:
    if not stages:
        return 0.0
    weights = {"succeeded": 1.0, "skipped": 1.0, "warning": 1.0, "failed": 1.0, "running": 0.5, "pending": 0.0}
    value = sum(weights.get(stage["status"], 0.0) for stage in stages) / len(stages)
    return round(value, 3)


def _count_by_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except ValueError:
        return None
    return round(max(0.0, delta.total_seconds()), 3)


def _number(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) else None
