from __future__ import annotations

import argparse
import csv
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml
from pyspark import StorageLevel
from pyspark.sql import functions as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.runner import SparkPipelineRunner
from spark_jobs.affinity import affinity_config, build_affinity_outputs
from spark_jobs.anomaly import anomaly_config, build_anomaly_outputs
from spark_jobs.cleaning import clean_events
from spark_jobs.experimentation import build_experiment_outputs, experiment_config
from spark_jobs.feature_mart import build_feature_mart_outputs, feature_mart_config
from spark_jobs.lifecycle import build_lifecycle_outputs, lifecycle_config
from spark_jobs.optimization import optimization_config, solve_merchandising_plan
from spark_jobs.recommendation import build_recommendation_outputs, recommendation_config
from spark_jobs.readers import read_events
from spark_jobs.session import build_spark
from scripts.collect_spark_history_metrics import collect_metrics as collect_spark_history_metrics


TaskResult = dict[str, object]


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def timed(task: Callable[[], int]) -> tuple[float, int]:
    started = time.perf_counter()
    output_rows = task()
    return round(time.perf_counter() - started, 4), output_rows


def pandas_frame(input_path: str, limit_rows: int | None) -> pd.DataFrame:
    read_kwargs = {"nrows": limit_rows} if limit_rows else {}
    df = pd.read_csv(input_path, **read_kwargs)
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce", utc=True)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["event_type"].isin(["view", "cart", "remove_from_cart", "purchase"])]
    df = df[df["event_time"].notna()]
    df = df[(df["price"].isna()) | ((df["price"] >= 0) & (df["price"] <= 100000))]
    return df.drop_duplicates(subset=["event_time", "event_type", "product_id", "user_id", "user_session"])


def run_pandas_tasks(input_path: str, limit_rows: int | None, profile: str) -> list[TaskResult]:
    results: list[TaskResult] = []
    load_started = time.perf_counter()
    df = pandas_frame(input_path, limit_rows)
    load_duration = round(time.perf_counter() - load_started, 4)

    tasks: dict[str, Callable[[], int]] = {
        "event_type_count": lambda: len(df.groupby("event_type").size()),
        "daily_events": lambda: len(df.groupby(df["event_time"].dt.date).size()),
        "top_categories": lambda: len(df.groupby("category_code").size().sort_values(ascending=False).head(20)),
    }

    for task_name, task in tasks.items():
        duration, output_rows = timed(task)
        results.append(
            result_row(
                engine="pandas",
                profile=profile,
                input_path=input_path,
                input_rows=len(df),
                task_name=task_name,
                duration_seconds=duration,
                output_rows=output_rows,
                limit_rows=limit_rows,
                extra={"load_seconds": load_duration},
            )
        )
    return results


def run_spark_tasks(config: dict, profile: str, history_url: str | None = None) -> list[TaskResult]:
    spark_config = config.get("spark", {})
    data_config = config.get("data", {})
    limit_rows = data_config.get("limit")
    input_path = data_config["input_path"]

    spark = build_spark(
        app_name=f"{config.get('app', {}).get('name', 'ecommerce')}-benchmark",
        master=spark_config.get("master"),
        configs=spark_runtime_configs(spark_config),
    )

    df = None
    results: list[TaskResult] = []
    spark_application_id = ""
    try:
        load_started = time.perf_counter()
        raw_df = read_events(
            spark,
            input_path=input_path,
            input_format=data_config.get("input_format", "csv"),
            delimiter=data_config.get("delimiter", ","),
        )
        if limit_rows:
            raw_df = raw_df.limit(int(limit_rows))
        df = clean_events(raw_df).persist(StorageLevel.MEMORY_AND_DISK)
        input_rows = df.count()
        load_duration = round(time.perf_counter() - load_started, 4)
        spark_application_id = spark.sparkContext.applicationId

        tasks: dict[str, Callable[[], int]] = {
            "event_type_count": lambda: df.groupBy("event_type").count().count(),
            "daily_events": lambda: df.groupBy("event_date").count().count(),
            "top_categories": lambda: (
                df.groupBy("category_code").count().orderBy(F.desc("count")).limit(20).count()
            ),
        }
        tasks.update(experiment_tasks(config, df, profile))

        for task_name, task in tasks.items():
            duration, output_rows = timed(task)
            results.append(
                result_row(
                    engine="spark",
                    profile=profile,
                    input_path=input_path,
                    input_rows=input_rows,
                    task_name=task_name,
                    duration_seconds=duration,
                    output_rows=output_rows,
                    limit_rows=limit_rows,
                    extra={
                        "load_seconds": load_duration,
                        "spark_partitions": df.rdd.getNumPartitions(),
                        "spark_application_id": spark_application_id,
                        "spark_application_status": "SUCCEEDED",
                        "cleaned_rows_per_second": round(input_rows / load_duration, 3) if load_duration else 0.0,
                        "driver_peak_memory_mb": driver_peak_memory_mb(),
                        "executor_peak_memory_mb": None,
                        "shuffle_read_bytes": None,
                        "shuffle_write_bytes": None,
                        "memory_spill_bytes": None,
                        "disk_spill_bytes": None,
                        "failed_task_count": None,
                        "retried_task_count": None,
                    },
                )
            )
    finally:
        if df is not None:
            df.unpersist()
        spark.stop()
    if results and history_url and spark_application_id:
        history_metrics = maybe_collect_history_metrics(history_url, spark_application_id)
        for row in results:
            row.update(history_metrics)
    return results


def experiment_tasks(config: dict, df, profile: str) -> dict[str, Callable[[], int]]:
    if profile == "affinity":
        return {
            "affinity_pipeline": lambda: len(
                build_affinity_outputs(
                    df,
                    affinity_config(config.get("affinity")),
                    run_id=f"benchmark-{profile}",
                    input_snapshot={"actual_input_path": config["data"]["input_path"]},
                )[1]["affinity_edges"]
            )
        }
    if profile == "recommendation":
        return {
            "recommendation_pipeline": lambda: int(
                build_recommendation_outputs(
                    df,
                    [],
                    recommendation_config({**config.get("recommendation", {}), "preview_limit": 100}),
                    output_dir=Path(config["data"].get("output_dir", "data/cache")) / "benchmark_recommendation",
                    run_id=f"benchmark-{profile}",
                    input_snapshot={"actual_input_path": config["data"]["input_path"]},
                )[1]["recommendation_summary"]["recommendation_count"]
            )
        }
    if profile == "anomaly":
        def anomaly_count() -> int:
            frames, feature_metrics = build_feature_mart_outputs(
                df,
                df,
                feature_mart_config({**config.get("feature_mart", {}), "preview_limit": 20}),
                run_id=f"benchmark-{profile}",
                input_snapshot={"actual_input_path": config["data"]["input_path"]},
            )
            _, metrics = build_anomaly_outputs(
                frames["daily_category_behavior"],
                frames["daily_product_behavior"],
                feature_metrics["feature_mart_quality"],
                feature_metrics["feature_mart_freshness"],
                anomaly_config({**config.get("anomaly", {}), "max_product_entities": 0}),
                run_id=f"benchmark-{profile}",
            )
            return int(metrics["anomaly_summary"]["signal_count"])

        return {"anomaly_pipeline": anomaly_count}
    if profile == "experimentation":
        def experimentation_count() -> int:
            frames, feature_metrics = build_feature_mart_outputs(
                df,
                df,
                feature_mart_config({**config.get("feature_mart", {}), "preview_limit": 20}),
                run_id=f"benchmark-{profile}",
                input_snapshot={"actual_input_path": config["data"]["input_path"]},
            )
            lifecycle_frames, _ = build_lifecycle_outputs(
                frames["daily_user_behavior"],
                frames["daily_category_behavior"],
                lifecycle_config(config.get("lifecycle")),
                run_id=f"benchmark-{profile}",
            )
            _, metrics = build_experiment_outputs(
                lifecycle_frames["user_lifecycle"],
                df.sparkSession.createDataFrame(
                    [],
                    "user_session string, product_id string, rank int, fallback_used boolean, confidence double",
                ),
                solve_merchandising_plan([], optimization_config(config.get("optimization"))).selected,
                experiment_config(config.get("experimentation")),
                run_id=f"benchmark-{profile}",
            )
            return int(metrics["experiment_summary"]["assignment_rows"])

        return {"experimentation_pipeline": experimentation_count}
    return {}


def run_pipeline_benchmark(config_path: str | Path, profile: str, history_url: str | None = None) -> list[TaskResult]:
    config = load_config(config_path)
    runner = SparkPipelineRunner(Path(__file__).resolve().parent.parent)
    result = runner.run(config_path, run_id=f"benchmark-{profile}")
    manifest = result.manifest or {}
    metrics = manifest.get("quality_report", {}).get("metrics", {})
    history_metrics = maybe_collect_history_metrics(history_url, str(manifest.get("spark_application_id") or ""))
    return [
        result_row(
            engine="spark",
            profile=profile,
            input_path=config["data"]["input_path"],
            input_rows=int(metrics.get("raw_rows") or 0),
            task_name="full_pipeline",
            duration_seconds=result.elapsed_seconds,
            output_rows=int(metrics.get("cleaned_rows") or 0),
            limit_rows=config["data"].get("limit"),
            extra={
                "success": result.succeeded,
                "error_message": result.stderr if not result.succeeded else "",
                "stdout_log_path": result.stdout_path or "",
                "stderr_log_path": result.stderr_path or "",
                "manifest_path": result.manifest_path or "",
                "quality_status": manifest.get("quality_status", ""),
                "spark_application_id": manifest.get("spark_application_id", ""),
                "spark_application_status": manifest.get("spark_application_status") or ("SUCCEEDED" if result.succeeded else "FAILED"),
                "cleaned_rows_per_second": manifest.get("cleaned_rows_per_second", 0.0),
                "driver_peak_memory_mb": manifest.get("driver_peak_memory_mb"),
                **history_metrics,
                "output_artifact_row_counts": json.dumps(manifest.get("output_artifact_row_counts", {}), ensure_ascii=False),
            },
        )
    ]


def spark_runtime_configs(spark_config: dict) -> dict[str, object]:
    configs = dict(spark_config.get("configs", {}))
    configs.update(
        {
            "spark.sql.shuffle.partitions": spark_config.get("shuffle_partitions", configs.get("spark.sql.shuffle.partitions", 4)),
            "spark.sql.session.timeZone": spark_config.get("timezone", configs.get("spark.sql.session.timeZone", "Asia/Shanghai")),
            "spark.sql.adaptive.enabled": configs.get("spark.sql.adaptive.enabled", "true"),
        }
    )
    return configs


def maybe_collect_history_metrics(history_url: str | None, app_id: str) -> dict[str, object]:
    keys = {
        "executor_peak_memory_mb": None,
        "shuffle_read_bytes": None,
        "shuffle_write_bytes": None,
        "memory_spill_bytes": None,
        "disk_spill_bytes": None,
        "failed_task_count": None,
        "retried_task_count": None,
        "spark_history_metrics_status": "not_requested",
        "spark_history_metrics_error": "",
    }
    if not history_url or not app_id:
        return keys
    attempts = max(1, int(os.getenv("SPARK_HISTORY_RETRY_ATTEMPTS", "12")))
    delay_seconds = max(0.0, float(os.getenv("SPARK_HISTORY_RETRY_SECONDS", "5")))
    last_error = ""
    for attempt in range(attempts):
        try:
            metrics = collect_spark_history_metrics(history_url, app_id)
            break
        except Exception as exc:
            last_error = str(exc)
            if attempt < attempts - 1 and delay_seconds:
                time.sleep(delay_seconds)
    else:
        keys["spark_history_metrics_status"] = "unavailable"
        keys["spark_history_metrics_error"] = last_error
        return keys
    keys.update(
        {
            "executor_peak_memory_mb": metrics.get("executor_peak_memory_mb"),
            "shuffle_read_bytes": metrics.get("shuffle_read_bytes"),
            "shuffle_write_bytes": metrics.get("shuffle_write_bytes"),
            "memory_spill_bytes": metrics.get("memory_spill_bytes"),
            "disk_spill_bytes": metrics.get("disk_spill_bytes"),
            "failed_task_count": metrics.get("failed_task_count"),
            "retried_task_count": metrics.get("retried_task_count"),
            "spark_history_metrics_status": "collected",
        }
    )
    return keys


def result_row(
    engine: str,
    profile: str,
    input_path: str,
    input_rows: int,
    task_name: str,
    duration_seconds: float,
    output_rows: int,
    limit_rows: int | None,
    extra: dict[str, object] | None = None,
) -> TaskResult:
    return {
        "engine": engine,
        "profile": profile,
        "input_path": input_path,
        "input_rows": int(input_rows),
        "task_name": task_name,
        "elapsed_seconds": duration_seconds,
        "duration_seconds": duration_seconds,
        "output_rows": int(output_rows),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "limit_rows": limit_rows,
        "success": True,
        "error_message": "",
        **(extra or {}),
    }


def write_results(output_dir: str | Path, results: list[TaskResult]) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "benchmark_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    fieldnames = sorted({key for row in results for key in row})
    with (target / "benchmark_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def driver_peak_memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_value = usage if sys.platform == "darwin" else usage * 1024
    return round(bytes_value / (1024 * 1024), 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Pandas and Spark aggregation performance.")
    parser.add_argument("--config", default="configs/local.yaml")
    parser.add_argument("--engines", default="pandas,spark", help="Comma separated: pandas,spark")
    parser.add_argument("--profile", default="tiny")
    parser.add_argument("--output-dir", default="data/benchmarks")
    parser.add_argument("--history-url", default="", help="Optional Spark History Server URL for pipeline metrics.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    engines = {engine.strip() for engine in args.engines.split(",") if engine.strip()}
    data_config = config["data"]
    input_path = data_config["input_path"]
    limit_rows = data_config.get("limit")

    results: list[TaskResult] = []
    if args.profile == "pipeline":
        write_results(args.output_dir, run_pipeline_benchmark(args.config, args.profile, args.history_url))
        print(f"Wrote 1 benchmark rows to {args.output_dir}")
        return
    if "pandas" in engines:
        if "*" in input_path or input_path.startswith("hdfs://"):
            print("Skipping pandas benchmark because input_path is not a single local file.")
        else:
            results.extend(run_pandas_tasks(input_path, int(limit_rows) if limit_rows else None, args.profile))
    if "spark" in engines:
        results.extend(run_spark_tasks(config, args.profile, args.history_url))

    write_results(args.output_dir, results)
    print(f"Wrote {len(results)} benchmark rows to {args.output_dir}")


if __name__ == "__main__":
    main()
