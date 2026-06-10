from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkSpec:
    sample: str
    variant: str
    result_path: str


BENCHMARK_SPECS = (
    BenchmarkSpec(
        sample="1pct",
        variant="baseline_local_csv",
        result_path="data/benchmarks/yarn-matrix-1pct-baseline-fixed-20260609/baseline_local_csv/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="1pct",
        variant="yarn_only_csv",
        result_path="data/benchmarks/yarn-matrix-1pct-20260609/yarn_only_csv/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="1pct",
        variant="yarn_aqe_csv",
        result_path="data/benchmarks/yarn-matrix-1pct-20260609/yarn_aqe_csv/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="1pct",
        variant="yarn_algorithm_csv",
        result_path="data/benchmarks/yarn-matrix-1pct-20260609/yarn_algorithm_csv/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="1pct",
        variant="yarn_parquet",
        result_path="data/benchmarks/yarn-matrix-1pct-20260609/yarn_parquet/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="5pct",
        variant="yarn_algorithm_csv",
        result_path="data/benchmarks/yarn-matrix-5pct-20260609/yarn_algorithm_csv/benchmark_results.json",
    ),
    BenchmarkSpec(
        sample="5pct",
        variant="yarn_parquet",
        result_path="data/benchmarks/yarn-matrix-5pct-20260609/yarn_parquet/benchmark_results.json",
    ),
)


HDFS_INPUTS = (
    {
        "sample": "1pct",
        "path": "hdfs:///user/course/ecommerce_behavior_user_sample_1pct/*.csv",
        "role": "csv_input",
        "size_label": "141.5 M",
    },
    {
        "sample": "5pct",
        "path": "hdfs:///user/course/ecommerce_behavior_user_sample_5pct/*.csv",
        "role": "csv_input",
        "size_label": "694.3 M",
    },
    {
        "sample": "1pct",
        "path": "hdfs:///user/course/ecommerce_behavior_processed_yarn_algorithm_1pct/events",
        "role": "parquet_input",
        "size_label": "128.5 M",
    },
    {
        "sample": "5pct",
        "path": "hdfs:///user/course/ecommerce_behavior_processed_yarn_algorithm_5pct/events",
        "role": "parquet_input",
        "size_label": "549.4 M",
    },
)

MODULE_BENCHMARK_DIR = Path("data/benchmarks/module-typical-20260610")
SCALE_BOUNDARY_PATH = Path("data/benchmarks/typical-scale-boundary-20260610.json")


class BenchmarkEvidenceService:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)

    def load(self) -> dict[str, Any]:
        runs = [row for spec in BENCHMARK_SPECS if (row := self._load_row(spec))]
        return {
            "benchmark_runs": runs,
            "benchmark_summary": self._summary(runs),
            "history_summary": self._history_summary(runs),
            "module_benchmark_runs": self._module_benchmark_runs(),
            "scale_boundary": self._scale_boundary(),
            "cluster_mode": self._cluster_mode(),
            "hdfs_inputs": list(HDFS_INPUTS),
            "local_samples": self._local_samples(),
            "cleanup_policy": {
                "raw_data_preserved": True,
                "kept_benchmark_dirs": [
                    "data/benchmarks/yarn-matrix-1pct-baseline-fixed-20260609",
                    "data/benchmarks/yarn-matrix-1pct-20260609",
                    "data/benchmarks/yarn-matrix-5pct-20260609",
                ],
                "kept_spark_history_app_ids": [
                    "application_1780991452919_0016",
                    "application_1780991452919_0017",
                    "application_1780991452919_0018",
                    "application_1780991452919_0019",
                    "application_1780991452919_0020",
                    "application_1780991452919_0021",
                ],
            },
        }

    def _load_row(self, spec: BenchmarkSpec) -> dict[str, Any] | None:
        path = self.project_root / spec.result_path
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not payload:
            return None
        row = payload[0]
        history_metrics = self._load_history_metrics(path.parent)
        elapsed = _number(row.get("elapsed_seconds"))
        output_rows = _number(row.get("output_rows"))
        rows_per_second = output_rows / elapsed if elapsed and output_rows is not None else None
        return {
            "sample": spec.sample,
            "variant": spec.variant,
            "status": "SUCCEEDED" if row.get("success") else "FAILED",
            "spark_application_id": row.get("spark_application_id"),
            "spark_application_status": row.get("spark_application_status"),
            "input_path": row.get("input_path"),
            "input_rows": row.get("input_rows"),
            "output_rows": row.get("output_rows"),
            "elapsed_seconds": elapsed,
            "rows_per_second": round(rows_per_second, 3) if rows_per_second else None,
            "quality_status": row.get("quality_status"),
            "driver_peak_memory_mb": row.get("driver_peak_memory_mb"),
            "spark_history_metrics_status": "collected" if history_metrics else row.get("spark_history_metrics_status"),
            "history_metrics": history_metrics,
            "task_count": history_metrics.get("task_count") if history_metrics else None,
            "failed_task_count": history_metrics.get("failed_task_count") if history_metrics else row.get("failed_task_count"),
            "retried_task_count": history_metrics.get("retried_task_count") if history_metrics else row.get("retried_task_count"),
            "shuffle_read_bytes": history_metrics.get("shuffle_read_bytes") if history_metrics else row.get("shuffle_read_bytes"),
            "shuffle_write_bytes": history_metrics.get("shuffle_write_bytes") if history_metrics else row.get("shuffle_write_bytes"),
            "memory_spill_bytes": history_metrics.get("memory_spill_bytes") if history_metrics else row.get("memory_spill_bytes"),
            "disk_spill_bytes": history_metrics.get("disk_spill_bytes") if history_metrics else row.get("disk_spill_bytes"),
            "result_path": spec.result_path,
        }

    def _load_history_metrics(self, result_dir: Path) -> dict[str, Any] | None:
        path = result_dir / "spark_history_metrics.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "collector": payload.get("collector"),
            "spark_application_id": payload.get("spark_application_id"),
            "spark_application_status": payload.get("spark_application_status"),
            "task_count": payload.get("task_count"),
            "failed_task_count": payload.get("failed_task_count"),
            "retried_task_count": payload.get("retried_task_count"),
            "shuffle_read_bytes": payload.get("shuffle_read_bytes"),
            "shuffle_write_bytes": payload.get("shuffle_write_bytes"),
            "memory_spill_bytes": payload.get("memory_spill_bytes"),
            "disk_spill_bytes": payload.get("disk_spill_bytes"),
            "executor_count": payload.get("executor_count"),
            "executor_peak_memory_mb": payload.get("executor_peak_memory_mb"),
            "driver_peak_memory_mb": payload.get("driver_peak_memory_mb"),
            "event_log_file_count": payload.get("event_log_file_count"),
            "event_log_compressed_bytes": payload.get("event_log_compressed_bytes"),
        }

    def _module_benchmark_runs(self) -> list[dict[str, Any]]:
        base = self.project_root / MODULE_BENCHMARK_DIR
        if not base.exists():
            return []
        rows: list[dict[str, Any]] = []
        for result_path in sorted(base.glob("*/benchmark_results.json")):
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            for row in payload:
                if row.get("task_name") not in {
                    "affinity_pipeline",
                    "recommendation_pipeline",
                    "anomaly_pipeline",
                    "experimentation_pipeline",
                }:
                    continue
                rel_path = result_path.relative_to(self.project_root)
                rows.append(
                    {
                        "profile": row.get("profile"),
                        "task_name": row.get("task_name"),
                        "input_rows": row.get("input_rows"),
                        "output_rows": row.get("output_rows"),
                        "elapsed_seconds": row.get("elapsed_seconds"),
                        "duration_seconds": row.get("duration_seconds"),
                        "success": bool(row.get("success")),
                        "spark_application_id": row.get("spark_application_id"),
                        "driver_peak_memory_mb": row.get("driver_peak_memory_mb"),
                        "result_path": str(rel_path),
                    }
                )
        return rows

    def _scale_boundary(self) -> dict[str, Any]:
        path = self.project_root / SCALE_BOUNDARY_PATH
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "policy": "typical_partial_only",
            "full_oct_nov_status": "not_run_by_request",
            "reason": "The formal evidence uses 1% and 5% representative user samples; full Oct+Nov is left as a resource-boundary extension.",
        }

    @staticmethod
    def _cluster_mode() -> dict[str, Any]:
        return {
            "status": "entrypoint_ready_not_default",
            "deploy_mode": "cluster",
            "config_path": "configs/yarn-cluster.yaml",
            "submit_script": "scripts/submit_yarn_cluster.sh",
            "default_refresh_mode": "client",
            "reason": "Flask currently reads local data/cache artifacts; cluster mode needs HDFS-backed output before becoming the default refresh path.",
        }

    def _local_samples(self) -> list[dict[str, Any]]:
        paths = [
            ("smoke", "data/sample/ecommerce_events.csv"),
            ("1pct", "data/sample/ecommerce_user_sample_1pct.csv"),
            ("5pct", "data/sample/ecommerce_user_sample_5pct.csv"),
            ("raw_oct", "data/raw/kaggle/ecommerce_behavior/2019-Oct.csv"),
            ("raw_nov", "data/raw/kaggle/ecommerce_behavior/2019-Nov.csv"),
        ]
        samples = []
        for name, rel_path in paths:
            path = self.project_root / rel_path
            if not path.exists():
                continue
            size_bytes = path.stat().st_size
            samples.append(
                {
                    "name": name,
                    "path": rel_path,
                    "size_bytes": size_bytes,
                    "size_label": _format_bytes(size_bytes),
                }
            )
        return samples

    @staticmethod
    def _summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
        by_variant = {(run["sample"], run["variant"]): run for run in runs}
        yarn_only = by_variant.get(("1pct", "yarn_only_csv"))
        yarn_aqe = by_variant.get(("1pct", "yarn_aqe_csv"))
        yarn_algorithm = by_variant.get(("1pct", "yarn_algorithm_csv"))
        yarn_algorithm_5pct = by_variant.get(("5pct", "yarn_algorithm_csv"))
        yarn_parquet_5pct = by_variant.get(("5pct", "yarn_parquet"))
        fastest_1pct = min(
            (run for run in runs if run["sample"] == "1pct" and run.get("elapsed_seconds")),
            key=lambda run: run["elapsed_seconds"],
            default=None,
        )
        return {
            "one_pct_run_count": sum(1 for run in runs if run["sample"] == "1pct"),
            "five_pct_run_count": sum(1 for run in runs if run["sample"] == "5pct"),
            "fastest_1pct_variant": fastest_1pct["variant"] if fastest_1pct else None,
            "yarn_only_to_aqe_speedup": _ratio(
                yarn_only.get("elapsed_seconds") if yarn_only else None,
                yarn_aqe.get("elapsed_seconds") if yarn_aqe else None,
            ),
            "yarn_only_to_algorithm_speedup": _ratio(
                yarn_only.get("elapsed_seconds") if yarn_only else None,
                yarn_algorithm.get("elapsed_seconds") if yarn_algorithm else None,
            ),
            "five_pct_algorithm_elapsed_seconds": yarn_algorithm_5pct.get("elapsed_seconds") if yarn_algorithm_5pct else None,
            "five_pct_parquet_elapsed_seconds": yarn_parquet_5pct.get("elapsed_seconds") if yarn_parquet_5pct else None,
            "interpretation": "YARN-only increased scheduling overhead; AQE and algorithm guards made runtime and memory risk controllable.",
        }

    @staticmethod
    def _history_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
        collected = [run for run in runs if run.get("spark_history_metrics_status") == "collected"]
        return {
            "collected_run_count": len(collected),
            "failed_task_count": sum(int(run.get("failed_task_count") or 0) for run in collected),
            "retried_task_count": sum(int(run.get("retried_task_count") or 0) for run in collected),
            "shuffle_read_bytes": sum(int(run.get("shuffle_read_bytes") or 0) for run in collected),
            "shuffle_write_bytes": sum(int(run.get("shuffle_write_bytes") or 0) for run in collected),
            "memory_spill_bytes": sum(int(run.get("memory_spill_bytes") or 0) for run in collected),
            "disk_spill_bytes": sum(int(run.get("disk_spill_bytes") or 0) for run in collected),
            "collector": "eventlog",
        }


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if not numerator or not denominator:
        return None
    return round(numerator / denominator, 3)


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"
