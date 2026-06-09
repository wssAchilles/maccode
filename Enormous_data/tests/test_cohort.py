from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.cohort import COHORT_CONTRACT_VERSION, build_cohort_outputs, cohort_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("cohort-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_cohort_outputs_retention_repurchase_and_quality(spark):
    rows = [
        {"event_time": "2019-10-01 00:00:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-10-20 00:00:00", "event_type": "purchase", "product_id": 2, "category_level1": "electronics", "price": 120.0, "user_id": 10, "user_session": "s2"},
        {"event_time": "2019-11-02 00:00:00", "event_type": "purchase", "product_id": 3, "category_level1": "appliances", "price": 80.0, "user_id": 10, "user_session": "s3"},
        {"event_time": "2019-10-03 00:00:00", "event_type": "purchase", "product_id": 4, "category_level1": "electronics", "price": 200.0, "user_id": 11, "user_session": "s4"},
        {"event_time": "2019-11-05 00:00:00", "event_type": "purchase", "product_id": 5, "category_level1": "electronics", "price": 90.0, "user_id": 11, "user_session": "s5"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_cohort_outputs(
        df,
        cohort_config({"min_cohort_users": 2, "preview_limit": 20}),
        run_id="cohort-test",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
    )

    summary = metrics["cohort_summary"]
    assert summary["contract_version"] == COHORT_CONTRACT_VERSION
    assert summary["quality_status"] == "passed"
    assert summary["purchase_user_count"] == 2
    assert summary["repeat_purchase_user_count"] == 2
    assert summary["repeat_purchase_rate"] == 1.0
    assert any(row["cohort"] == "2019-10" and row["period_index"] == 1 for row in metrics["cohort_retention_matrix"])
    assert any(row["bucket"] in {"same_month", "month_1"} for row in metrics["cohort_repurchase_intervals"])
    assert frames["cohort_matrix"].count() >= 2


def test_cohort_sparse_quality_needs_review(spark):
    rows = [
        {"event_time": "2019-10-01 00:00:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_cohort_outputs(
        df,
        cohort_config({"min_cohort_users": 5}),
        run_id="cohort-sparse",
        input_snapshot={},
    )

    assert metrics["cohort_summary"]["quality_status"] == "needs_review"
    assert metrics["cohort_quality"]["sparse_cohorts"] == ["2019-10"]


def test_cohort_quality_ignores_incomplete_tail_month(spark):
    rows = [
        {"event_time": "2019-10-01 00:00:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-10-02 00:00:00", "event_type": "purchase", "product_id": 2, "category_level1": "electronics", "price": 120.0, "user_id": 11, "user_session": "s2"},
        {"event_time": "2019-11-03 00:00:00", "event_type": "purchase", "product_id": 3, "category_level1": "electronics", "price": 90.0, "user_id": 10, "user_session": "s3"},
        {"event_time": "2019-11-04 00:00:00", "event_type": "purchase", "product_id": 4, "category_level1": "electronics", "price": 95.0, "user_id": 11, "user_session": "s4"},
        {"event_time": "2019-12-01 00:00:00", "event_type": "purchase", "product_id": 5, "category_level1": "electronics", "price": 80.0, "user_id": 12, "user_session": "s5"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_cohort_outputs(
        df,
        cohort_config({"min_cohort_users": 2, "min_cohort_observation_days": 7}),
        run_id="cohort-incomplete-tail",
        input_snapshot={},
    )

    assert metrics["cohort_summary"]["quality_status"] == "passed"
    assert metrics["cohort_quality"]["sparse_cohorts"] == []
    assert metrics["cohort_quality"]["incomplete_cohorts"] == ["2019-12"]


def test_cohort_preview_limit_keeps_summary_statistics(spark):
    rows = [
        {
            "event_time": "2019-10-01 00:00:00",
            "event_type": "purchase",
            "product_id": idx,
            "category_level1": f"cat-{idx}",
            "price": 50.0 + idx,
            "user_id": idx,
            "user_session": f"s{idx}",
        }
        for idx in range(6)
    ]
    rows.extend(
        [
            {
                "event_time": "2019-10-02 00:00:00",
                "event_type": "purchase",
                "product_id": 100,
                "category_level1": "cat-0",
                "price": 60.0,
                "user_id": 0,
                "user_session": "s0-repeat",
            },
            {
                "event_time": "2019-11-02 00:00:00",
                "event_type": "purchase",
                "product_id": 101,
                "category_level1": "cat-1",
                "price": 61.0,
                "user_id": 1,
                "user_session": "s1-repeat",
            },
            {
                "event_time": "2019-12-02 00:00:00",
                "event_type": "purchase",
                "product_id": 102,
                "category_level1": "cat-2",
                "price": 62.0,
                "user_id": 2,
                "user_session": "s2-repeat",
            },
            {
                "event_time": "2020-01-02 00:00:00",
                "event_type": "purchase",
                "product_id": 103,
                "category_level1": "cat-3",
                "price": 63.0,
                "user_id": 3,
                "user_session": "s3-repeat",
            },
        ]
    )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_cohort_outputs(
        df,
        cohort_config({"preview_limit": 1, "min_cohort_users": 1}),
        run_id="cohort-preview",
        input_snapshot={},
    )

    assert len(metrics["cohort_segments"]) == 1
    assert len(metrics["cohort_retention_matrix"]) == 1
    assert len(metrics["cohort_repurchase_intervals"]) == 1
    assert frames["cohort_segments"].count() > len(metrics["cohort_segments"])
    assert frames["cohort_matrix"].count() > len(metrics["cohort_retention_matrix"])
    assert metrics["cohort_summary"]["purchase_user_count"] == 6
