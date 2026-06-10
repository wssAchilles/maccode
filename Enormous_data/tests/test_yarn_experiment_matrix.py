from __future__ import annotations

from scripts.run_yarn_experiment_matrix import matrix_configs


def test_matrix_configs_define_csv_and_parquet_comparison_variants():
    base = {
        "app": {"name": "base"},
        "spark": {
            "master": "yarn",
            "configs": {
                "spark.sql.adaptive.enabled": True,
                "spark.sql.adaptive.coalescePartitions.enabled": True,
                "spark.sql.adaptive.skewJoin.enabled": True,
                "spark.sql.adaptive.localShuffleReader.enabled": True,
            },
        },
        "data": {
            "input_path": "hdfs:///old/*.csv",
            "input_format": "csv",
            "output_dir": "data/cache",
            "processed_dir": "hdfs:///old_processed",
        },
        "storage": {"mode": "hdfs"},
    }

    configs = matrix_configs(base, "5pct")

    assert configs["baseline_local_csv"]["spark"]["master"] == "local[*]"
    assert configs["baseline_local_csv"]["data"]["input_path"] == "file:///app/data/sample/ecommerce_user_sample_5pct.csv"
    assert configs["baseline_local_csv"]["data"]["processed_dir"].startswith("file:///")
    assert configs["yarn_only_csv"]["spark"]["configs"]["spark.sql.adaptive.enabled"] is False
    assert configs["yarn_aqe_csv"]["spark"]["configs"]["spark.sql.adaptive.skewJoin.enabled"] is True
    assert configs["yarn_algorithm_csv"]["data"]["input_path"] == "hdfs:///user/course/ecommerce_behavior_user_sample_5pct/*.csv"
    assert configs["yarn_parquet"]["data"]["input_format"] == "parquet"
    assert configs["yarn_parquet"]["data"]["input_path"].endswith("/events")
