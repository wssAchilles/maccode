from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


def fetch_json(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"failed to fetch Spark History API: {url}") from exc


def _completed_from_app(app: Any) -> bool:
    if not isinstance(app, dict):
        return False
    attempts = app.get("attempts")
    if not isinstance(attempts, list):
        return False
    return any(isinstance(attempt, dict) and bool(attempt.get("completed")) for attempt in attempts)


def collect_metrics(base_url: str, app_id: str, include_jobs: bool = False) -> dict[str, Any]:
    encoded_app_id = quote(app_id, safe="")
    app = fetch_json(base_url, f"/api/v1/applications/{encoded_app_id}")
    stages = fetch_json(base_url, f"/api/v1/applications/{encoded_app_id}/stages")
    executors = fetch_json(base_url, f"/api/v1/applications/{encoded_app_id}/executors")
    jobs_api_status = "skipped"
    jobs_api_error = ""
    jobs: Any = []
    if include_jobs:
        try:
            jobs = fetch_json(base_url, f"/api/v1/applications/{encoded_app_id}/jobs")
            jobs_api_status = "collected"
        except RuntimeError as exc:
            jobs_api_status = "unavailable"
            jobs_api_error = str(exc)

    stage_attempts = [stage for stage in stages if isinstance(stage, dict)]
    executor_rows = [executor for executor in executors if isinstance(executor, dict)]
    job_rows = [job for job in jobs if isinstance(job, dict)]
    failed_jobs = [job for job in job_rows if str(job.get("status", "")).upper() not in {"SUCCEEDED", "RUNNING"}]
    failed_task_count = sum(int(stage.get("numFailedTasks") or 0) for stage in stage_attempts)
    if include_jobs and jobs_api_status == "collected":
        application_status = "FAILED" if failed_jobs else "SUCCEEDED"
    elif _completed_from_app(app):
        application_status = "COMPLETED"
    else:
        application_status = "UNKNOWN"

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "spark_application_id": app_id,
        "spark_application_name": app.get("name") if isinstance(app, dict) else None,
        "spark_application_status": application_status,
        "jobs_api_status": jobs_api_status,
        "jobs_api_error": jobs_api_error,
        "job_count": len(job_rows) if include_jobs and jobs_api_status == "collected" else None,
        "failed_job_count": len(failed_jobs) if include_jobs and jobs_api_status == "collected" else None,
        "stage_attempt_count": len(stage_attempts),
        "task_count": sum(int(stage.get("numTasks") or 0) for stage in stage_attempts),
        "failed_task_count": failed_task_count,
        "retried_task_count": sum(
            max(0, int(stage.get("numCompleteTasks") or 0) + int(stage.get("numFailedTasks") or 0) - int(stage.get("numTasks") or 0))
            for stage in stage_attempts
        ),
        "shuffle_read_bytes": sum(int(stage.get("shuffleReadBytes") or 0) for stage in stage_attempts),
        "shuffle_write_bytes": sum(int(stage.get("shuffleWriteBytes") or 0) for stage in stage_attempts),
        "memory_spill_bytes": sum(int(stage.get("memoryBytesSpilled") or 0) for stage in stage_attempts),
        "disk_spill_bytes": sum(int(stage.get("diskBytesSpilled") or 0) for stage in stage_attempts),
        "executor_count": len([executor for executor in executor_rows if executor.get("id") != "driver"]),
        "executor_peak_memory_mb": round(
            max((int(executor.get("memoryUsed") or 0) for executor in executor_rows if executor.get("id") != "driver"), default=0)
            / (1024 * 1024),
            2,
        ),
        "driver_peak_memory_mb": round(
            max((int(executor.get("memoryUsed") or 0) for executor in executor_rows if executor.get("id") == "driver"), default=0)
            / (1024 * 1024),
            2,
        ),
    }


def write_metrics(output_dir: str | Path, metrics: dict[str, Any]) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "spark_history_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    with (target / "spark_history_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(metrics))
        writer.writeheader()
        writer.writerow(metrics)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Spark History Server metrics for benchmark evidence.")
    parser.add_argument("--history-url", default="http://127.0.0.1:28080")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--output-dir", default="data/benchmarks/spark-history")
    parser.add_argument(
        "--include-jobs",
        action="store_true",
        help="Also call the History /jobs API. Use only for small event logs; stages/executors are enough for spill, shuffle, and task metrics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = collect_metrics(args.history_url, args.app_id, include_jobs=args.include_jobs)
    write_metrics(args.output_dir, metrics)
    print(f"Wrote Spark History metrics for {args.app_id} to {args.output_dir}")


if __name__ == "__main__":
    main()
