from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_command(command: list[str], *, stdout: Any = subprocess.PIPE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, stdout=stdout, stderr=subprocess.PIPE)


def list_eventlog_files(app_id: str, container: str, hdfs_bin: str) -> list[str]:
    event_dir = f"/spark-history/eventlog_v2_{app_id}"
    result = run_command(["docker", "exec", container, hdfs_bin, "dfs", "-ls", event_dir])
    files: list[str] = []
    for line in result.stdout.splitlines():
        path = line.rsplit(maxsplit=1)[-1] if line.strip() else ""
        if path.endswith(".zstd"):
            files.append(path)
    return sorted(files)


def copy_eventlog_files(app_id: str, container: str, hdfs_bin: str, target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    local_paths: list[Path] = []
    for hdfs_path in list_eventlog_files(app_id, container, hdfs_bin):
        name = Path(hdfs_path).name
        container_path = f"/tmp/{name}"
        host_path = target / name
        run_command(["docker", "exec", container, hdfs_bin, "dfs", "-copyToLocal", "-f", hdfs_path, container_path])
        run_command(["docker", "cp", f"{container}:{container_path}", str(host_path)])
        run_command(["docker", "exec", container, "rm", "-f", container_path])
        local_paths.append(host_path)
    return local_paths


def _number(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _task_failed(event: dict[str, Any]) -> bool:
    task_info = event.get("Task Info") or {}
    if task_info.get("Failed") or task_info.get("Killed"):
        return True
    reason = event.get("Task End Reason") or {}
    return str(reason.get("Reason", "")).lower() not in {"success", ""}


def _shuffle_read_bytes(metrics: dict[str, Any]) -> int:
    shuffle = metrics.get("Shuffle Read Metrics") or {}
    push = shuffle.get("Push Based Shuffle") or {}
    return sum(
        _number(shuffle.get(key))
        for key in ("Remote Bytes Read", "Remote Bytes Read To Disk", "Local Bytes Read")
    ) + sum(
        _number(push.get(key))
        for key in ("Merged Remote Bytes Read", "Merged Local Bytes Read")
    )


def parse_eventlog_files(files: list[Path], app_id: str) -> dict[str, Any]:
    if not files:
        raise RuntimeError(f"no event log files found for {app_id}")

    metrics = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collector": "eventlog",
        "spark_application_id": app_id,
        "spark_application_name": None,
        "spark_application_status": "UNKNOWN",
        "job_count": 0,
        "failed_job_count": 0,
        "stage_attempt_count": 0,
        "task_count": 0,
        "failed_task_count": 0,
        "retried_task_count": 0,
        "shuffle_read_bytes": 0,
        "shuffle_write_bytes": 0,
        "memory_spill_bytes": 0,
        "disk_spill_bytes": 0,
        "executor_count": 0,
        "executor_peak_memory_mb": 0.0,
        "driver_peak_memory_mb": 0.0,
        "event_log_file_count": len(files),
        "event_log_compressed_bytes": sum(path.stat().st_size for path in files),
    }
    executor_ids: set[str] = set()
    task_keys: set[tuple[int, int, int]] = set()
    failed_jobs = 0
    completed = False

    for path in files:
        process = subprocess.Popen(
            ["zstd", "-dc", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        for line in process.stdout:
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_name = event.get("Event")
            if event_name == "SparkListenerApplicationStart":
                metrics["spark_application_name"] = event.get("App Name")
            elif event_name == "SparkListenerApplicationEnd":
                completed = True
            elif event_name == "SparkListenerExecutorAdded":
                executor_id = str(event.get("Executor ID") or "")
                if executor_id and executor_id != "driver":
                    executor_ids.add(executor_id)
            elif event_name == "SparkListenerBlockManagerAdded":
                block_manager = event.get("Block Manager ID") or {}
                executor_id = str(block_manager.get("Executor ID") or "")
                maximum_memory_mb = round(_number(event.get("Maximum Memory")) / (1024 * 1024), 2)
                if executor_id == "driver":
                    metrics["driver_peak_memory_mb"] = max(float(metrics["driver_peak_memory_mb"]), maximum_memory_mb)
                elif executor_id:
                    executor_ids.add(executor_id)
                    metrics["executor_peak_memory_mb"] = max(float(metrics["executor_peak_memory_mb"]), maximum_memory_mb)
            elif event_name == "SparkListenerJobEnd":
                metrics["job_count"] += 1
                result = event.get("Job Result") or {}
                if str(result.get("Result", "")).lower() not in {"jobsucceeded", "success"}:
                    failed_jobs += 1
            elif event_name == "SparkListenerStageCompleted":
                metrics["stage_attempt_count"] += 1
            elif event_name == "SparkListenerTaskEnd":
                metrics["task_count"] += 1
                stage_id = _number(event.get("Stage ID"))
                attempt_id = _number(event.get("Stage Attempt ID"))
                task_info = event.get("Task Info") or {}
                partition_id = _number(task_info.get("Partition ID"))
                key = (stage_id, attempt_id, partition_id)
                if key in task_keys or _number(task_info.get("Attempt")) > 0:
                    metrics["retried_task_count"] += 1
                task_keys.add(key)
                if _task_failed(event):
                    metrics["failed_task_count"] += 1
                task_metrics = event.get("Task Metrics") or {}
                metrics["shuffle_read_bytes"] += _shuffle_read_bytes(task_metrics)
                shuffle_write = task_metrics.get("Shuffle Write Metrics") or {}
                metrics["shuffle_write_bytes"] += _number(shuffle_write.get("Shuffle Bytes Written"))
                metrics["memory_spill_bytes"] += _number(task_metrics.get("Memory Bytes Spilled"))
                metrics["disk_spill_bytes"] += _number(task_metrics.get("Disk Bytes Spilled"))
                peak_memory_mb = round(_number(task_metrics.get("Peak Execution Memory")) / (1024 * 1024), 2)
                metrics["executor_peak_memory_mb"] = max(float(metrics["executor_peak_memory_mb"]), peak_memory_mb)
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"zstd failed for {path}: {stderr.strip()}")

    metrics["executor_count"] = len(executor_ids)
    metrics["failed_job_count"] = failed_jobs
    metrics["spark_application_status"] = "SUCCEEDED" if completed and failed_jobs == 0 and metrics["failed_task_count"] == 0 else "FAILED"
    return metrics


def write_metrics(output_dir: str | Path, metrics: dict[str, Any]) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "spark_history_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    with (target / "spark_history_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(metrics))
        writer.writeheader()
        writer.writerow(metrics)


def collect_from_hdfs_eventlog(app_id: str, output_dir: str | Path, container: str, hdfs_bin: str) -> dict[str, Any]:
    if shutil.which("zstd") is None:
        raise RuntimeError("zstd command is required to parse Spark event logs")
    with tempfile.TemporaryDirectory(prefix=f"spark-eventlog-{app_id}-") as tmp:
        files = copy_eventlog_files(app_id, container, hdfs_bin, Path(tmp))
        metrics = parse_eventlog_files(files, app_id)
    write_metrics(output_dir, metrics)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Spark metrics by parsing HDFS rolling event logs.")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--container", default="enormous-data-yarn-namenode")
    parser.add_argument("--hdfs-bin", default="/opt/hadoop/bin/hdfs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = collect_from_hdfs_eventlog(args.app_id, args.output_dir, args.container, args.hdfs_bin)
    print(
        f"Wrote eventlog metrics for {args.app_id}: "
        f"tasks={metrics['task_count']}, shuffle_read={metrics['shuffle_read_bytes']}, spill={metrics['memory_spill_bytes']}"
    )


if __name__ == "__main__":
    main()
