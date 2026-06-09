from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.jobs.repository import JobRepository
from app.jobs.service import JobService
from app.pipeline.runner import PipelineResult, SparkPipelineRunner
from app.services.spark_runner import SparkJobRunningError


class ImmediateRunner:
    def __init__(self, result: PipelineResult):
        self.result = result
        self.run_id = None

    def run(self, config_path, run_id=None):
        self.run_id = run_id
        return self.result


class BlockingRunner:
    def run(self, config_path, run_id=None):
        time.sleep(0.2)
        return PipelineResult(returncode=0, elapsed_seconds=0.2, stdout="Spark job finished", stderr="")


def write_config(path):
    path.write_text(
        """
app:
  name: test
data:
  input_path: data/raw/*.csv
storage:
  mode: local
""".strip(),
        encoding="utf-8",
    )


def make_service(tmp_path, runner):
    config_path = tmp_path / "spark.yaml"
    write_config(config_path)
    cache_dir = tmp_path / "cache"
    repository = JobRepository(tmp_path / "platform.db")
    return JobService(
        repository=repository,
        runner=runner,
        project_root=tmp_path,
        config_path=config_path,
        cache_dir=cache_dir,
    ), repository, cache_dir


def wait_for_status(repository: JobRepository, job_id: str, status: str):
    deadline = time.time() + 2
    while time.time() < deadline:
        job = repository.get(job_id)
        if job and job.status == status:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach {status}")


def test_job_service_records_successful_refresh(tmp_path, monkeypatch):
    monkeypatch.delenv("SPARK_HISTORY_URL", raising=False)
    runner = ImmediateRunner(
        PipelineResult(
            returncode=0,
            elapsed_seconds=0.1,
            stdout="Spark run manifest: data/cache/runs/run-1/manifest.json\nSpark job finished",
            stderr="",
            manifest={
                "run_id": "run-1",
                "contract_version": "pipeline-run-governance/v1",
                "config_hash": "abc123",
                "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
                "quality_status": "passed",
                "quality_report": {"gate": {"status": "passed"}, "metrics": {"cleaned_rows": 100}},
                "output_artifacts": {"metrics_dir": "data/cache"},
                "spark_application_id": "application_1",
                "spark_application_status": "SUCCEEDED",
                "failure_stage": None,
            },
        )
    )
    service, repository, cache_dir = make_service(tmp_path, runner)

    queued = service.enqueue_refresh()
    completed = wait_for_status(repository, queued.job_id, "succeeded")

    assert queued.status == "queued"
    assert runner.run_id == queued.run_id
    assert "Spark job finished" in completed.message
    assert completed.elapsed_seconds == 0.1
    assert completed.contract_version == "pipeline-run-governance/v1"
    assert completed.input_snapshot["actual_input_path"].startswith("hdfs://master:9000/")
    assert completed.quality_status == "passed"
    assert completed.spark_application_id == "application_1"
    assert completed.spark_application_status == "SUCCEEDED"
    assert completed.spark_history_metrics_status == "not_configured"
    assert completed.quality_report["metrics"]["cleaned_rows"] == 100
    assert repository.latest().job_id == queued.job_id
    assert (cache_dir / "job.json").exists()


def test_job_service_records_best_effort_spark_history_metrics(tmp_path, monkeypatch):
    def fake_collect(history_url, app_id):
        assert history_url == "http://history:18080"
        assert app_id == "application_2"
        return {
            "spark_application_id": app_id,
            "spark_application_status": "SUCCEEDED",
            "failed_task_count": 0,
            "memory_spill_bytes": 0,
        }

    monkeypatch.setenv("SPARK_HISTORY_URL", "http://history:18080")
    monkeypatch.setattr("app.jobs.service.collect_spark_history_metrics", fake_collect)
    runner = ImmediateRunner(
        PipelineResult(
            returncode=0,
            elapsed_seconds=0.1,
            stdout="Spark run manifest: data/cache/runs/run-2/manifest.json\nSpark job finished",
            stderr="",
            manifest={
                "run_id": "run-2",
                "spark_application_id": "application_2",
                "spark_application_status": "SUCCEEDED",
                "quality_status": "passed",
            },
        )
    )
    service, repository, _ = make_service(tmp_path, runner)

    queued = service.enqueue_refresh()
    completed = wait_for_status(repository, queued.job_id, "succeeded")

    assert completed.spark_application_id == "application_2"
    assert completed.spark_application_status == "SUCCEEDED"
    assert completed.spark_history_metrics_status == "collected"
    assert completed.spark_history_metrics_error == ""
    assert completed.spark_history_metrics["failed_task_count"] == 0


def test_job_service_retries_spark_history_metrics_collection(tmp_path, monkeypatch):
    calls = []

    def fake_collect(history_url, app_id):
        calls.append((history_url, app_id))
        if len(calls) == 1:
            raise RuntimeError("history server is still indexing")
        return {
            "spark_application_id": app_id,
            "spark_application_status": "SUCCEEDED",
            "failed_task_count": 0,
            "disk_spill_bytes": 0,
        }

    monkeypatch.setenv("SPARK_HISTORY_URL", "http://history:18080")
    monkeypatch.setenv("SPARK_HISTORY_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("SPARK_HISTORY_RETRY_SECONDS", "0")
    monkeypatch.setattr("app.jobs.service.collect_spark_history_metrics", fake_collect)
    runner = ImmediateRunner(
        PipelineResult(
            returncode=0,
            elapsed_seconds=0.1,
            stdout="Spark run manifest: data/cache/runs/run-3/manifest.json\nSpark job finished",
            stderr="",
            manifest={
                "run_id": "run-3",
                "spark_application_id": "application_3",
                "spark_application_status": "SUCCEEDED",
                "quality_status": "passed",
            },
        )
    )
    service, repository, _ = make_service(tmp_path, runner)

    queued = service.enqueue_refresh()
    completed = wait_for_status(repository, queued.job_id, "succeeded")

    assert calls == [("http://history:18080", "application_3"), ("http://history:18080", "application_3")]
    assert completed.spark_history_metrics_status == "collected"
    assert completed.spark_history_metrics_error == ""
    assert completed.spark_history_metrics["disk_spill_bytes"] == 0


def test_job_service_records_failed_refresh(tmp_path):
    service, repository, _ = make_service(
        tmp_path,
        ImmediateRunner(PipelineResult(returncode=1, elapsed_seconds=0.1, stdout="", stderr="input path not found")),
    )

    queued = service.enqueue_refresh()
    completed = wait_for_status(repository, queued.job_id, "failed")

    assert completed.error == "input path not found"
    assert completed.message == "input path not found"


def test_job_service_rejects_concurrent_refresh(tmp_path):
    service, _, _ = make_service(tmp_path, BlockingRunner())

    first = service.enqueue_refresh()

    with pytest.raises(SparkJobRunningError):
        service.enqueue_refresh()

    assert first.job_id


def test_pipeline_runner_uses_submit_script(monkeypatch, tmp_path):
    calls = {}

    class Completed:
        returncode = 0
        stdout = "Spark job finished"
        stderr = ""

    def fake_run(command, cwd, text, capture_output, check):
        calls["command"] = command
        calls["cwd"] = cwd
        calls["text"] = text
        calls["capture_output"] = capture_output
        calls["check"] = check
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = SparkPipelineRunner(tmp_path, submit_script=Path("/app/scripts/submit_yarn_client.sh"))

    result = runner.run("configs/yarn-client.yaml", run_id="run-yarn")

    assert result.succeeded
    assert calls["command"] == ["/app/scripts/submit_yarn_client.sh", "configs/yarn-client.yaml", "run-yarn"]
    assert calls["cwd"] == tmp_path
