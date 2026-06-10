from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_eventlog_metrics import collect_from_hdfs_eventlog

BENCHMARK_RESULT_FILES = (
    "data/benchmarks/yarn-matrix-1pct-20260609/yarn_only_csv/benchmark_results.json",
    "data/benchmarks/yarn-matrix-1pct-20260609/yarn_aqe_csv/benchmark_results.json",
    "data/benchmarks/yarn-matrix-1pct-20260609/yarn_algorithm_csv/benchmark_results.json",
    "data/benchmarks/yarn-matrix-1pct-20260609/yarn_parquet/benchmark_results.json",
    "data/benchmarks/yarn-matrix-5pct-20260609/yarn_algorithm_csv/benchmark_results.json",
    "data/benchmarks/yarn-matrix-5pct-20260609/yarn_parquet/benchmark_results.json",
)


def load_first_row(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"empty benchmark result: {path}")
    return payload[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Spark event log metrics for formal YARN benchmark runs.")
    parser.add_argument("--container", default="enormous-data-yarn-namenode")
    parser.add_argument("--hdfs-bin", default="/opt/hadoop/bin/hdfs")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary: list[dict[str, Any]] = []
    for rel_path in BENCHMARK_RESULT_FILES:
        result_path = PROJECT_ROOT / rel_path
        row = load_first_row(result_path)
        app_id = str(row.get("spark_application_id") or "")
        if not app_id.startswith("application_"):
            continue
        output_dir = result_path.parent
        metrics_path = output_dir / "spark_history_metrics.json"
        if metrics_path.exists() and not args.force:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        else:
            metrics = collect_from_hdfs_eventlog(app_id, output_dir, args.container, args.hdfs_bin)
        summary.append(
            {
                "result_path": rel_path,
                "spark_application_id": app_id,
                "collector": metrics.get("collector"),
                "task_count": metrics.get("task_count"),
                "failed_task_count": metrics.get("failed_task_count"),
                "retried_task_count": metrics.get("retried_task_count"),
                "shuffle_read_bytes": metrics.get("shuffle_read_bytes"),
                "shuffle_write_bytes": metrics.get("shuffle_write_bytes"),
                "memory_spill_bytes": metrics.get("memory_spill_bytes"),
                "disk_spill_bytes": metrics.get("disk_spill_bytes"),
            }
        )
    output = PROJECT_ROOT / "data/benchmarks/spark-history-eventlog-backfill.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(summary)} backfilled metric summaries to {output}")


if __name__ == "__main__":
    main()
