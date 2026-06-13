from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cleaning import clean_events
from spark_jobs.feature_mart import (
    add_event_keys,
    build_feature_mart_outputs,
    feature_mart_config,
)


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("feature-mart-test")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    yield session
    session.stop()


def make_raw(spark):
    rows = [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:05:00 UTC", "cart", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:10:00 UTC", "purchase", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-02 01:00:00 UTC", "view", 201, 2, "apparel.shoes", "nike", 50.0, 2, "s2"),
        ("2019-10-02 01:10:00 UTC", "purchase", 201, 2, "apparel.shoes", "nike", 50.0, 2, "s2"),
        ("2019-10-02 02:00:00 UTC", "bad_event", 301, 3, "apparel.shoes", "adidas", 50.0, 3, "s3"),
    ]
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
    return spark.createDataFrame(rows, schema=schema)


def test_feature_mart_builds_deduped_daily_facts(spark):
    raw = make_raw(spark)
    cleaned = clean_events(raw).persist()

    frames, metrics = build_feature_mart_outputs(
        raw,
        cleaned,
        feature_mart_config({"max_freshness_lag_hours": 100000}),
        run_id="feature-test",
        input_snapshot={"actual_input_path": "unit-test"},
    )

    product_rows = {
        (str(row["dt"]), str(row["product_id"])): row.asDict()
        for row in frames["daily_product_behavior"].collect()
    }
    assert product_rows[("2019-10-01", "101")]["views"] == 1
    assert product_rows[("2019-10-01", "101")]["purchases"] == 1
    assert product_rows[("2019-10-01", "101")]["view_to_purchase_rate"] == 1.0
    assert metrics["feature_mart_summary"]["contract_version"] == "behavior-feature-mart/v1"
    assert metrics["feature_mart_partitions"]["written"] == 2
    assert metrics["feature_mart_quality"]["invalid_event_type_rows"] == 1
    assert metrics["feature_mart_features"][0]["chinese_name"]
    assert metrics["feature_mart_readiness"]["total_features"] == len(metrics["feature_mart_features"])


def test_event_key_is_stable_for_duplicate_events(spark):
    cleaned = clean_events(make_raw(spark))
    keyed = add_event_keys(cleaned)
    duplicate_keys = (
        keyed.groupBy("event_key")
        .count()
        .filter("count > 1")
        .collect()
    )

    assert len(duplicate_keys) == 0
    assert keyed.select("event_key").distinct().count() == keyed.count()


def test_feature_mart_quality_gate_rejects_strict_quarantine_threshold(spark):
    raw = make_raw(spark)
    cleaned = clean_events(raw).persist()

    _, metrics = build_feature_mart_outputs(
        raw,
        cleaned,
        feature_mart_config({"max_quarantined_rate": 0.0}),
        run_id="feature-test-rejected",
        input_snapshot={"actual_input_path": "unit-test"},
    )

    assert metrics["feature_mart_quality"]["quality_status"] == "failed"
    assert any(not check["passed"] for check in metrics["feature_mart_quality"]["checks"])
