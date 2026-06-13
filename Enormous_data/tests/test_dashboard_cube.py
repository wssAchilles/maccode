from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.dashboard_cube import build_dashboard_cube_outputs
from spark_jobs.dashboard_semantics import DASHBOARD_CUBE_ALL_VALUE, DASHBOARD_CUBE_CONTRACT_VERSION


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("dashboard-cube-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_dashboard_cube_builds_exact_summary_and_daily_grains(spark):
    rows = [
        ("2020-01-01", "view", "electronics", "apple", 100.0, 1, "s1"),
        ("2020-01-01", "purchase", "electronics", "apple", 100.0, 1, "s1"),
        ("2020-01-02", "purchase", "electronics", "samsung", 200.0, 1, "s2"),
        ("2020-01-02", "purchase", "apparel", "nike", 300.0, 2, "s3"),
        ("2020-01-02", "cart", "apparel", "nike", 300.0, 3, "s4"),
    ]
    df = spark.createDataFrame(
        rows,
        ["event_date", "event_type", "category_level1", "brand", "price", "user_id", "user_session"],
    )

    frames, metrics = build_dashboard_cube_outputs(
        df,
        run_id="cube-test",
        input_snapshot={"actual_input_path": "unit-test"},
    )

    total_rows = {(_row_key(row)): row.asDict() for row in frames["dashboard_cube_total"].collect()}
    daily_rows = {(_row_key(row)): row.asDict() for row in frames["dashboard_cube_daily"].collect()}
    all_key = (DASHBOARD_CUBE_ALL_VALUE, DASHBOARD_CUBE_ALL_VALUE, DASHBOARD_CUBE_ALL_VALUE, DASHBOARD_CUBE_ALL_VALUE)
    electronics_purchase_key = (
        DASHBOARD_CUBE_ALL_VALUE,
        "purchase",
        "electronics",
        DASHBOARD_CUBE_ALL_VALUE,
    )
    apparel_daily_key = ("2020-01-02", DASHBOARD_CUBE_ALL_VALUE, "apparel", DASHBOARD_CUBE_ALL_VALUE)

    assert total_rows[all_key]["event_count"] == 5
    assert total_rows[all_key]["purchase_count"] == 3
    assert total_rows[all_key]["total_sales"] == 600.0
    assert total_rows[all_key]["unique_users"] == 3
    assert total_rows[electronics_purchase_key]["event_count"] == 2
    assert total_rows[electronics_purchase_key]["unique_users"] == 1
    assert total_rows[electronics_purchase_key]["unique_sessions"] == 2
    assert daily_rows[apparel_daily_key]["event_count"] == 2
    assert daily_rows[apparel_daily_key]["purchase_count"] == 1
    assert daily_rows[apparel_daily_key]["total_sales"] == 300.0
    assert metrics["dashboard_cube_summary"]["contract_version"] == DASHBOARD_CUBE_CONTRACT_VERSION
    assert metrics["dashboard_cube_summary"]["cube_row_count"] == (
        metrics["dashboard_cube_summary"]["summary_cube_rows"] + metrics["dashboard_cube_summary"]["daily_cube_rows"]
    )
    assert metrics["dashboard_semantic_metrics"][0]["chinese_name"] == "事件量"
    assert metrics["dashboard_semantic_metrics"][0]["source"] == "dashboard_metric_cube"


def _row_key(row):
    return (row["dt"], row["event_type"], row["category_level1"], row["brand"])
