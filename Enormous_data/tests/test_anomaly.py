from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.anomaly import ANOMALY_CONTRACT_VERSION, anomaly_config, build_anomaly_outputs, build_daily_signals, score_daily_signals


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
    assert metrics["anomaly_incidents"]
    assert metrics["anomaly_root_cause"]
    assert metrics["anomaly_evaluation"]["incidents"]["incident_count"] >= 1
    assert "weekday" in metrics["anomaly_rules"]["baseline"]


def test_anomaly_baseline_excludes_current_point(spark):
    signals = spark.createDataFrame(
        [
            {"dt": "2019-10-01", "entity_type": "category", "entity_id": "electronics", "entity_label": "electronics", "metric": "revenue", "value": 500.0},
            {"dt": "2019-10-02", "entity_type": "category", "entity_id": "electronics", "entity_label": "electronics", "metric": "revenue", "value": 510.0},
            {"dt": "2019-10-03", "entity_type": "category", "entity_id": "electronics", "entity_label": "electronics", "metric": "revenue", "value": 490.0},
            {"dt": "2019-10-04", "entity_type": "category", "entity_id": "electronics", "entity_label": "electronics", "metric": "revenue", "value": 5000.0},
        ]
    )

    spike = (
        score_daily_signals(
            signals,
            anomaly_config({"warning_z": 2.0, "critical_z": 4.0, "min_baseline_points": 3}),
            run_id="anomaly-trailing",
        )
        .filter("dt = '2019-10-04'")
        .first()
    )

    assert spike["baseline_points"] == 3
    assert spike["baseline_median"] <= 510
    assert spike["severity"] == "critical"


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


def test_cleaning_bot_fraud_filter(spark):
    from spark_jobs.cleaning import clean_events
    rows = []
    # 正常 Session（7 天）
    for day in range(1, 8):
        dt = f"2019-10-{day:02d}"
        rows.append({"event_time": f"{dt} 10:00:00", "event_type": "view", "product_id": 1, "category_code": "electronics", "brand": "apple", "price": 100.0, "user_id": 1, "user_session": "normal-session"})
        rows.append({"event_time": f"{dt} 10:05:00", "event_type": "purchase", "product_id": 1, "category_code": "electronics", "brand": "apple", "price": 100.0, "user_id": 1, "user_session": "normal-session"})

    # 恶意高频 Session（同一秒内触发 20 次事件，不同商品以防止去重）
    dt_bot = "2019-10-01"
    for s in range(20):
        rows.append({
            "event_time": f"{dt_bot} 12:00:00", 
            "event_type": "view", 
            "product_id": s, 
            "category_code": "electronics", 
            "brand": "apple", 
            "price": 100.0, 
            "user_id": 999, 
            "user_session": "bot-session"
        })

    df = spark.createDataFrame(rows)
    cleaned = clean_events(df)
    
    rem_sessions = {r["user_session"] for r in cleaned.collect()}
    assert "normal-session" in rem_sessions
    assert "bot-session" not in rem_sessions


def test_anomaly_predictive_residual(spark):
    # 历史销量 500，第 4 天爆发至 5000
    daily_category = spark.createDataFrame(
        [
            {"dt": "2019-10-01", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "revenue": 500.0, "avg_price": 100.0, "conversion_rate": 0.05},
            {"dt": "2019-10-02", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "revenue": 500.0, "avg_price": 100.0, "conversion_rate": 0.05},
            {"dt": "2019-10-03", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "revenue": 500.0, "avg_price": 100.0, "conversion_rate": 0.05},
            {"dt": "2019-10-04", "category_level1": "electronics", "views": 1000, "carts": 100, "purchases": 50, "unique_users": 800, "revenue": 5000.0, "avg_price": 100.0, "conversion_rate": 0.05},
        ]
    )
    daily_product = spark.createDataFrame(
        [{"dt": "2019-10-01", "product_id": "1001", "brand": "apple", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 5, "unique_users": 80, "unique_sessions": 90, "revenue": 500.0, "avg_price": 100.0, "view_to_cart_rate": 0.1, "cart_to_purchase_rate": 0.5, "view_to_purchase_rate": 0.05}]
    )

    # 传入大促期间的合理预测值，期望为 5000，置信边界包含实际值 5000
    forecasting_series = [
        {
            "dt": "2019-10-04",
            "scope": "category",
            "entity_key": "electronics",
            "metric": "gmv",
            "forecast_value": 5000.0,
            "lower_bound": 4000.0,
            "upper_bound": 6000.0,
        }
    ]

    _, metrics = build_anomaly_outputs(
        daily_category,
        daily_product,
        {"quality_status": "passed"},
        {"sla_status": "passed"},
        anomaly_config({"warning_z": 2.0, "critical_z": 4.0, "min_baseline_points": 3}),
        run_id="anomaly-residual-test",
        forecasting_series=forecasting_series,
    )

    alerts = metrics["anomaly_alerts"]
    # 验证因落在合理预测空间，该脉冲警报已被自适应免除
    category_revenue_alerts = [
        a for a in alerts 
        if a["entity_id"] == "electronics" and a["metric"] == "revenue" and a["dt"] == "2019-10-04"
    ]
    assert not category_revenue_alerts
