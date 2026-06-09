from __future__ import annotations

from scripts import collect_spark_history_metrics


def test_collect_metrics_skips_jobs_api_by_default(monkeypatch):
    calls: list[str] = []

    def fake_fetch_json(base_url: str, path: str):
        calls.append(path)
        if path.endswith("/jobs"):
            raise AssertionError("jobs API should be skipped by default")
        if path.endswith("/stages"):
            return [
                {
                    "numTasks": 4,
                    "numCompleteTasks": 4,
                    "numFailedTasks": 0,
                    "shuffleReadBytes": 1024,
                    "shuffleWriteBytes": 2048,
                    "memoryBytesSpilled": 0,
                    "diskBytesSpilled": 0,
                }
            ]
        if path.endswith("/executors"):
            return [{"id": "driver", "memoryUsed": 64 * 1024 * 1024}, {"id": "1", "memoryUsed": 128 * 1024 * 1024}]
        return {"name": "pipeline", "attempts": [{"completed": True}]}

    monkeypatch.setattr(collect_spark_history_metrics, "fetch_json", fake_fetch_json)

    metrics = collect_spark_history_metrics.collect_metrics("http://history:18080", "application_1")

    assert not any(path.endswith("/jobs") for path in calls)
    assert metrics["jobs_api_status"] == "skipped"
    assert metrics["job_count"] is None
    assert metrics["spark_application_status"] == "COMPLETED"
    assert metrics["task_count"] == 4
    assert metrics["failed_task_count"] == 0
    assert metrics["shuffle_read_bytes"] == 1024
    assert metrics["executor_peak_memory_mb"] == 128


def test_collect_metrics_keeps_stage_metrics_when_jobs_api_fails(monkeypatch):
    def fake_fetch_json(base_url: str, path: str):
        if path.endswith("/jobs"):
            raise RuntimeError("failed to fetch Spark History API: http://history/jobs")
        if path.endswith("/stages"):
            return [
                {
                    "numTasks": 2,
                    "numCompleteTasks": 3,
                    "numFailedTasks": 1,
                    "shuffleReadBytes": 10,
                    "shuffleWriteBytes": 20,
                    "memoryBytesSpilled": 30,
                    "diskBytesSpilled": 40,
                }
            ]
        if path.endswith("/executors"):
            return []
        return {"name": "pipeline", "attempts": [{"completed": True}]}

    monkeypatch.setattr(collect_spark_history_metrics, "fetch_json", fake_fetch_json)

    metrics = collect_spark_history_metrics.collect_metrics(
        "http://history:18080",
        "application_2",
        include_jobs=True,
    )

    assert metrics["jobs_api_status"] == "unavailable"
    assert "failed to fetch Spark History API" in metrics["jobs_api_error"]
    assert metrics["job_count"] is None
    assert metrics["failed_job_count"] is None
    assert metrics["task_count"] == 2
    assert metrics["failed_task_count"] == 1
    assert metrics["retried_task_count"] == 2
    assert metrics["memory_spill_bytes"] == 30
