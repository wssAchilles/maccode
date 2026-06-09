from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.attribution import ATTRIBUTION_CONTRACT_VERSION, attribution_config, build_attribution_outputs
from spark_jobs.cleaning import clean_events


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("attribution-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    yield session
    session.stop()


def make_cleaned(spark):
    schema = [
        "event_time",
        "event_type",
        "product_id",
        "category_id",
        "category_code",
        "brand",
        "price",
        "user_id",
        "user_session",
    ]
    rows = [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 00:05:00 UTC", "cart", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 00:10:00 UTC", "view", 102, 1, "electronics.phone", "brand-b", 200.0, 1, "s1"),
        ("2019-10-01 00:15:00 UTC", "purchase", 102, 1, "electronics.phone", "brand-b", 200.0, 1, "s1"),
        ("2019-10-01 01:00:00 UTC", "view", 201, 2, "apparel.shoes", "brand-c", 80.0, 2, "s2"),
        ("2019-10-01 01:10:00 UTC", "purchase", 201, 2, "apparel.shoes", "brand-c", 80.0, 2, "s2"),
    ]
    return clean_events(spark.createDataFrame(rows, schema=schema)).persist()


def test_attribution_outputs_models_entities_and_assists(spark):
    cleaned = make_cleaned(spark)
    config = attribution_config({"min_purchase_rows": 2, "min_attribution_coverage_rate": 0.5, "preview_limit": 50})

    _frames, metrics = build_attribution_outputs(
        cleaned,
        config,
        run_id="attr-test",
        input_snapshot={
            "configured_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
        },
    )

    summary = metrics["attribution_summary"]
    quality = metrics["attribution_quality"]
    category_rows = [row for row in metrics["attribution_entities"] if row["entity_type"] == "category"]

    assert summary["contract_version"] == ATTRIBUTION_CONTRACT_VERSION
    assert summary["purchase_rows"] == 2
    assert summary["attribution_coverage_rate"] == 1.0
    assert summary["total_purchase_revenue"] == 280.0
    assert summary["avg_touchpoints_before_purchase"] == 2.0
    assert quality["quality_status"] == "needs_review"
    assert "history_days" in quality["warnings"]
    assert {row["entity_type"] for row in metrics["attribution_models"]} == {"brand", "category", "product"}
    assert category_rows[0]["time_decay_assisted_revenue"] > 0
    assert metrics["attribution_assists"][0]["priority_score"] > 0
    assert metrics["attribution_paths"][0]["purchase_sessions"] >= 1


def test_attribution_quality_fails_without_purchases(spark):
    schema = [
        "event_time",
        "event_type",
        "product_id",
        "category_id",
        "category_code",
        "brand",
        "price",
        "user_id",
        "user_session",
    ]
    rows = [("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1")]
    cleaned = clean_events(spark.createDataFrame(rows, schema=schema)).persist()

    _frames, metrics = build_attribution_outputs(
        cleaned,
        attribution_config({"min_purchase_rows": 1}),
        run_id="attr-empty",
        input_snapshot={"configured_input_path": "input.csv", "actual_input_path": "input.csv"},
    )

    assert metrics["attribution_quality"]["quality_status"] == "failed"
    assert "no_purchase_rows" in metrics["attribution_quality"]["warnings"]
