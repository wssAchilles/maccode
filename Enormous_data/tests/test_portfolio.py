from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.portfolio import PORTFOLIO_CONTRACT_VERSION, build_portfolio_outputs, portfolio_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("portfolio-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_portfolio_outputs_mix_price_bands_concentration_and_quality(spark):
    rows = [
        {"event_time": "2019-10-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "brand": "apple", "price": 100.0},
        {"event_time": "2019-10-01 00:01:00", "event_type": "cart", "product_id": 1, "category_level1": "electronics", "brand": "apple", "price": 100.0},
        {"event_time": "2019-10-01 00:02:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "brand": "apple", "price": 100.0},
        {"event_time": "2019-10-02 00:00:00", "event_type": "view", "product_id": 2, "category_level1": "electronics", "brand": "samsung", "price": 1200.0},
        {"event_time": "2019-10-02 00:02:00", "event_type": "purchase", "product_id": 2, "category_level1": "electronics", "brand": "samsung", "price": 1200.0},
        {"event_time": "2019-10-03 00:00:00", "event_type": "view", "product_id": 3, "category_level1": "apparel", "brand": "nike", "price": 40.0},
        {"event_time": "2019-10-03 00:02:00", "event_type": "purchase", "product_id": 3, "category_level1": "apparel", "brand": "nike", "price": 40.0},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_portfolio_outputs(
        df,
        portfolio_config({"min_purchase_rows": 2, "min_history_days": 3, "preview_limit": 20}),
        run_id="portfolio-test",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
    )

    summary = metrics["portfolio_summary"]
    assert summary["contract_version"] == PORTFOLIO_CONTRACT_VERSION
    assert summary["quality_status"] == "passed"
    assert summary["total_revenue"] == 1340.0
    assert summary["price_band_count"] == 3
    assert any(row["category_level1"] == "electronics" and row["revenue"] == 1300.0 for row in metrics["portfolio_category_mix"])
    assert any(row["price_band"] == "luxury" and row["purchases"] == 1 for row in metrics["portfolio_price_bands"])
    assert metrics["portfolio_product_concentration"][0]["product_id"] == 2
    assert metrics["portfolio_opportunities"]
    assert frames["portfolio_category_mix"].count() == 2


def test_portfolio_quality_needs_review_for_sparse_history(spark):
    rows = [
        {"event_time": "2019-10-01 00:00:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "brand": "apple", "price": 100.0},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_portfolio_outputs(
        df,
        portfolio_config({"min_purchase_rows": 5, "min_history_days": 7}),
        run_id="portfolio-sparse",
        input_snapshot={},
    )

    assert metrics["portfolio_summary"]["quality_status"] == "needs_review"
    assert "purchase_rows" in metrics["portfolio_quality"]["warnings"]
    assert "history_days" in metrics["portfolio_quality"]["warnings"]
