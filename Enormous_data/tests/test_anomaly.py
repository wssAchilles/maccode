from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.anomaly import ANOMALY_CONTRACT_VERSION, anomaly_config, build_anomaly_outputs, build_daily_signals


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("anomaly-radar-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_build_anomaly_outputs_detects_category_revenue_spike(spark):
    daily_category = spark.createDataFrame(
        [
            {"dt": "2019-10-01", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "revenue": 500.0, "avg_price": 100.0, "conversion_rate": 0.05},
            {"dt": "2019-10-02", "category_level1": "electronics", "views": 105, "carts": 11, "purchases": 5, "unique_users": 82, "revenue": 510.0, "avg_price": 102.0, "conversion_rate": 0.047619},
            {"dt": "2019-10-03", "category_level1": "electronics", "views": 98, "carts": 10, "purchases": 5, "unique_users": 76, "revenue": 490.0, "avg_price": 98.0, "conversion_rate": 0.05102},
            {"dt": "2019-10-04", "category_level1": "electronics", "views": 110, "carts": 12, "purchases": 6, "unique_users": 84, "revenue": 5000.0, "avg_price": 833.3, "conversion_rate": 0.054545},
        ]
    )
    daily_product = spark.createDataFrame(
        [
            {"dt": "2019-10-01", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "unique_sessions": 90, "revenue": 500.0, "avg_price": 100.0, "view_to_cart_rate": 0.1, "cart_to_purchase_rate": 0.5, "view_to_purchase_rate": 0.05},
            {"dt": "2019-10-02", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 105, "carts": 11, "purchases": 5, "unique_users": 82, "unique_sessions": 91, "revenue": 510.0, "avg_price": 102.0, "view_to_cart_rate": 0.104762, "cart_to_purchase_rate": 0.454545, "view_to_purchase_rate": 0.047619},
            {"dt": "2019-10-03", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 98, "carts": 10, "purchases": 5, "unique_users": 76, "unique_sessions": 88, "revenue": 490.0, "avg_price": 98.0, "view_to_cart_rate": 0.102041, "cart_to_purchase_rate": 0.5, "view_to_purchase_rate": 0.05102},
            {"dt": "2019-10-04", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 110, "carts": 12, "purchases": 6, "unique_users": 84, "unique_sessions": 96, "revenue": 5000.0, "avg_price": 833.3, "view_to_cart_rate": 0.109091, "cart_to_purchase_rate": 0.5, "view_to_purchase_rate": 0.054545},
        ]
    )

    _, metrics = build_anomaly_outputs(
        daily_category,
        daily_product,
        {"quality_status": "passed"},
        {"sla_status": "passed"},
        anomaly_config({"warning_z": 2.0, "critical_z": 4.0, "min_baseline_points": 3}),
        run_id="anomaly-test",
    )

    assert metrics["anomaly_summary"]["contract_version"] == ANOMALY_CONTRACT_VERSION
    assert metrics["anomaly_summary"]["alert_count"] >= 1
    assert any(alert["metric"] == "revenue" and alert["direction"] == "spike" for alert in metrics["anomaly_alerts"])
    assert metrics["anomaly_rules"]["baseline"].startswith("median")


def test_build_anomaly_outputs_promotes_feature_mart_control_alerts(spark):
    daily_category = spark.createDataFrame(
        [{"dt": "2019-10-01", "category_level1": "electronics", "views": 10, "carts": 1, "purchases": 1, "unique_users": 8, "revenue": 100.0, "avg_price": 100.0, "conversion_rate": 0.1}]
    )
    daily_product = spark.createDataFrame(
        [{"dt": "2019-10-01", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 10, "carts": 1, "purchases": 1, "unique_users": 8, "unique_sessions": 9, "revenue": 100.0, "avg_price": 100.0, "view_to_cart_rate": 0.1, "cart_to_purchase_rate": 1.0, "view_to_purchase_rate": 0.1}]
    )

    _, metrics = build_anomaly_outputs(
        daily_category,
        daily_product,
        {"quality_status": "failed"},
        {"sla_status": "stale"},
        anomaly_config(None),
        run_id="anomaly-control",
    )

    codes = {alert["alert_code"] for alert in metrics["anomaly_alerts"]}
    assert "feature_mart_quality_failed" in codes
    assert "feature_mart_freshness_stale" in codes
    assert metrics["anomaly_summary"]["radar_status"] == "critical"


def test_build_anomaly_outputs_marks_insufficient_baseline_without_alerts(spark):
    daily_category = spark.createDataFrame(
        [{"dt": "2019-10-01", "category_level1": "electronics", "views": 10, "carts": 1, "purchases": 1, "unique_users": 8, "revenue": 100.0, "avg_price": 100.0, "conversion_rate": 0.1}]
    )
    daily_product = spark.createDataFrame(
        [{"dt": "2019-10-01", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 10, "carts": 1, "purchases": 1, "unique_users": 8, "unique_sessions": 9, "revenue": 100.0, "avg_price": 100.0, "view_to_cart_rate": 0.1, "cart_to_purchase_rate": 1.0, "view_to_purchase_rate": 0.1}]
    )

    _, metrics = build_anomaly_outputs(
        daily_category,
        daily_product,
        {"quality_status": "passed"},
        {"sla_status": "passed"},
        anomaly_config({"min_baseline_points": 3}),
        run_id="anomaly-short-baseline",
    )

    assert metrics["anomaly_summary"]["radar_status"] == "insufficient_baseline"
    assert metrics["anomaly_summary"]["watch_count"] > 0


def test_daily_signals_can_disable_product_entities(spark):
    daily_category = spark.createDataFrame(
        [{"dt": "2019-10-01", "category_level1": "electronics", "views": 10, "purchases": 1, "revenue": 100.0, "conversion_rate": 0.1}]
    )
    daily_product = spark.createDataFrame(
        [{"dt": "2019-10-01", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 10, "purchases": 1, "revenue": 100.0, "view_to_purchase_rate": 0.1}]
    )

    rows = build_daily_signals(daily_category, daily_product, max_product_entities=0).collect()

    assert rows
    assert {row["entity_type"] for row in rows} == {"category"}
