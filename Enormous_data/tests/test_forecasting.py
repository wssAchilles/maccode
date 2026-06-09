from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.forecasting import FORECAST_CONTRACT_VERSION, build_forecasting_outputs, forecasting_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("forecasting-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_forecasting_outputs_sparse_fallback_and_quality_gate(spark):
    rows = [
        {"event_time": "2019-11-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "price": 999.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:01:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:02:00", "event_type": "purchase", "product_id": 2, "category_level1": "apparel", "price": 50.0, "user_id": 11, "user_session": "s2"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 3, "min_history_days": 7, "top_entities": 2}),
        run_id="forecast-test",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv", "storage_mode": "hdfs"},
    )

    summary = metrics["forecasting_summary"]
    assert summary["contract_version"] == FORECAST_CONTRACT_VERSION
    assert summary["site_forecast_gmv"] == 450.0
    assert summary["site_forecast_purchase_count"] == 6.0
    assert summary["quality_status"] == "needs_review"
    assert summary["history_days"] == 1
    assert metrics["forecasting_quality"]["passed"] is False
    assert any(row["fallback_reason"] == "insufficient_history_days" for row in metrics["forecasting_entities"])
    assert any(row["metric"] == "gmv" for row in metrics["forecasting_series"])


def test_forecasting_backtest_generates_error_rows_when_history_exists(spark):
    rows = []
    for day, price in [("2019-11-01", 100.0), ("2019-11-02", 120.0), ("2019-11-03", 80.0)]:
        rows.append(
            {
                "event_time": f"{day} 00:00:00",
                "event_type": "purchase",
                "product_id": 1,
                "category_level1": "electronics",
                "price": price,
                "user_id": 10,
                "user_session": f"s-{day}",
            }
        )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 2, "backtest_window_days": 1, "min_history_days": 2}),
        run_id="forecast-backtest",
        input_snapshot={},
    )

    assert metrics["forecasting_backtest"]
    assert metrics["forecasting_quality"]["metrics"]["site_wape"] is not None
    assert metrics["forecasting_summary"]["history_days"] == 3


def test_forecasting_excludes_incomplete_trailing_day_from_quality(spark):
    rows = []
    for index in range(10):
        day = f"2019-11-{index + 1:02d}"
        price = 10.0 if index == 9 else 100.0
        rows.append(
            {
                "event_time": f"{day} 00:00:00",
                "event_type": "purchase",
                "product_id": 1,
                "category_level1": "electronics",
                "price": price,
                "user_id": index,
                "user_session": f"s-{day}",
            }
        )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"backtest_window_days": 2, "min_history_days": 2}),
        run_id="forecast-incomplete-tail",
        input_snapshot={},
    )

    quality = metrics["forecasting_quality"]
    assert quality["metrics"]["excluded_incomplete_dates"] == ["2019-11-10"]
    assert metrics["forecasting_summary"]["history_range"]["max_dt"] == "2019-11-09"


def test_forecasting_collects_only_site_and_top_entities_for_driver_outputs(spark):
    rows = []
    for category_index in range(5):
        for day_index in range(2):
            rows.append(
                {
                    "event_time": f"2019-11-{day_index + 1:02d} 00:00:00",
                    "event_type": "purchase",
                    "product_id": category_index,
                    "category_level1": f"cat-{category_index}",
                    "price": 100.0 + category_index,
                    "user_id": category_index * 10 + day_index,
                    "user_session": f"s-{category_index}-{day_index}",
                }
            )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"top_entities": 2, "forecast_horizon_days": 1, "preview_limit": 20, "min_history_days": 1}),
        run_id="forecast-top-entities",
        input_snapshot={},
    )

    assert frames["daily_demand"].filter(F.col("scope") == "category").select("entity_key").distinct().count() == 5
    assert metrics["forecasting_summary"]["entity_count"] == 3
    assert {row["scope"] for row in metrics["forecasting_entities"]} == {"site", "category"}


def test_forecasting_caps_driver_history_rows(spark):
    rows = []
    for category_index in range(5):
        for day_index in range(4):
            rows.append(
                {
                    "event_time": f"2019-11-{day_index + 1:02d} 00:00:00",
                    "event_type": "purchase",
                    "product_id": category_index,
                    "category_level1": f"cat-{category_index}",
                    "price": 100.0 + category_index,
                    "user_id": category_index * 10 + day_index,
                    "user_session": f"s-{category_index}-{day_index}",
                }
            )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config(
            {
                "top_entities": 3,
                "forecast_horizon_days": 1,
                "history_collect_days": 10,
                "max_driver_history_rows": 8,
                "min_history_days": 1,
            }
        ),
        run_id="forecast-driver-cap",
        input_snapshot={},
    )

    quality_metrics = metrics["forecasting_quality"]["metrics"]
    assert quality_metrics["driver_history_rows"] <= 8
    assert quality_metrics["collected_history_days"] == 2
    assert metrics["forecasting_summary"]["max_driver_history_rows"] == 8
    assert any(check["name"] == "driver_history_rows" and check["passed"] for check in metrics["forecasting_quality"]["checks"])
