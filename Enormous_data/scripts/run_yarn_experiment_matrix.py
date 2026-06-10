from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_TAIL_CHARS = 12000


def deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def sample_paths(sample_label: str) -> tuple[str, str]:
    local_path = f"file:///app/data/sample/ecommerce_user_sample_{sample_label}.csv"
    hdfs_path = f"hdfs:///user/course/ecommerce_behavior_user_sample_{sample_label}/*.csv"
    return local_path, hdfs_path


def matrix_configs(base: dict[str, Any], sample_label: str) -> dict[str, dict[str, Any]]:
    local_sample, hdfs_sample = sample_paths(sample_label)
    optimized_processed = f"hdfs:///user/course/ecommerce_behavior_processed_yarn_algorithm_{sample_label}"
    common_yarn = {
        "data": {
            "input_path": hdfs_sample,
            "input_format": "csv",
            "output_dir": "data/cache",
        },
        "storage": {"mode": "hdfs", "fallback_to_local": False},
    }
    return {
        "baseline_local_csv": deep_update(
            base,
            {
                "app": {"name": f"ecommerce-baseline-local-{sample_label}"},
                "spark": {
                    "master": "local[*]",
                    "configs": {
                        "spark.eventLog.enabled": False,
                        "spark.sql.adaptive.enabled": False,
                    },
                },
                "data": {
                    "input_path": local_sample,
                    "input_format": "csv",
                    "processed_dir": f"file:///app/data/processed/ecommerce_behavior_baseline_{sample_label}",
                },
                "storage": {"mode": "local", "fallback_to_local": False},
            },
        ),
        "yarn_only_csv": deep_update(
            base,
            deep_update(
                common_yarn,
                {
                    "app": {"name": f"ecommerce-yarn-only-{sample_label}"},
                    "spark": {
                        "configs": {
                            "spark.sql.adaptive.enabled": False,
                            "spark.sql.adaptive.coalescePartitions.enabled": False,
                            "spark.sql.adaptive.skewJoin.enabled": False,
                            "spark.sql.adaptive.localShuffleReader.enabled": False,
                        }
                    },
                    "data": {"processed_dir": f"hdfs:///user/course/ecommerce_behavior_processed_yarn_only_{sample_label}"},
                },
            ),
        ),
        "yarn_aqe_csv": deep_update(
            base,
            deep_update(
                common_yarn,
                {
                    "app": {"name": f"ecommerce-yarn-aqe-{sample_label}"},
                    "spark": {
                        "configs": {
                            "spark.sql.adaptive.enabled": True,
                            "spark.sql.adaptive.coalescePartitions.enabled": True,
                            "spark.sql.adaptive.skewJoin.enabled": True,
                            "spark.sql.adaptive.localShuffleReader.enabled": True,
                        }
                    },
                    "data": {"processed_dir": f"hdfs:///user/course/ecommerce_behavior_processed_yarn_aqe_{sample_label}"},
                },
            ),
        ),
        "yarn_algorithm_csv": deep_update(
            base,
            deep_update(
                common_yarn,
                {
                    "app": {"name": f"ecommerce-yarn-algorithm-{sample_label}"},
                    "data": {"processed_dir": optimized_processed},
                },
            ),
        ),
        "yarn_parquet": deep_update(
            base,
            {
                "app": {"name": f"ecommerce-yarn-parquet-{sample_label}"},
                "data": {
                    "input_path": f"{optimized_processed}/events",
                    "input_format": "parquet",
                    "output_dir": "data/cache",
                    "processed_dir": f"hdfs:///user/course/ecommerce_behavior_processed_yarn_parquet_{sample_label}",
                },
                "storage": {"mode": "hdfs", "fallback_to_local": False},
            },
        ),
    }


def run_variant(config_path: Path, variant: str, output_dir: Path, history_url: str) -> dict[str, Any]:
    env = os.environ.copy()
    if variant.startswith("yarn_"):
        env["SPARK_SUBMIT_SCRIPT"] = str(PROJECT_ROOT / "scripts" / "submit_yarn_client.sh")
    else:
        env.pop("SPARK_SUBMIT_SCRIPT", None)

    command = [
        sys.executable,
        "scripts/benchmark.py",
        "--config",
        str(config_path),
        "--engines",
        "spark",
        "--profile",
        "pipeline",
        "--history-url",
        history_url if variant.startswith("yarn_") else "",
        "--output-dir",
        str(output_dir / variant),
    ]
    started = datetime.now(timezone.utc).isoformat()
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{variant}.stdout.log"
    stderr_path = log_dir / f"{variant}.stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )
    return {
        "variant": variant,
        "config_path": str(config_path),
        "output_dir": str(output_dir / variant),
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "returncode": result.returncode,
        "stdout": tail_text(stdout_path),
        "stderr": tail_text(stderr_path),
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
    }


def tail_text(path: Path, max_chars: int = LOG_TAIL_CHARS) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_chars))
        return handle.read().decode("utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the YARN experiment comparison matrix for a prepared user sample.")
    parser.add_argument("--base-config", default="configs/yarn-client.yaml")
    parser.add_argument("--sample-label", default="1pct", choices=["1pct", "5pct"])
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--history-url", default="http://spark-history-server:18080")
    parser.add_argument("--variants", default="baseline_local_csv,yarn_only_csv,yarn_aqe_csv,yarn_algorithm_csv,yarn_parquet")
    parser.add_argument("--write-configs-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_config = load_yaml(PROJECT_ROOT / args.base_config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = PROJECT_ROOT / (args.output_dir or f"data/benchmarks/yarn-matrix-{args.sample_label}-{stamp}")
    config_dir = output_dir / "configs"
    run_log: list[dict[str, Any]] = []
    configs = matrix_configs(base_config, args.sample_label)
    selected = [variant.strip() for variant in args.variants.split(",") if variant.strip()]

    for variant in selected:
        if variant not in configs:
            raise ValueError(f"unknown variant: {variant}")
        config_path = config_dir / f"{variant}.yaml"
        write_yaml(config_path, configs[variant])
        if not args.write_configs_only:
            run_log.append(run_variant(config_path, variant, output_dir, args.history_url))

    (output_dir / "matrix_run_log.json").write_text(json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote matrix configs and run log to {output_dir}")


if __name__ == "__main__":
    main()
