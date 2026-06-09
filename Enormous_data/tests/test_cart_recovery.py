from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cart_recovery import CART_RECOVERY_CONTRACT_VERSION, build_cart_recovery_outputs, cart_recovery_config
from spark_jobs.cleaning import clean_events


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("cart-recovery-test")
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
        ("2019-10-01 00:00:00 UTC", "cart", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 00:05:00 UTC", "purchase", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 01:00:00 UTC", "cart", 102, 1, "electronics.phone", "brand-b", 50.0, 2, "s2"),
        ("2019-10-01 02:00:00 UTC", "cart", 103, 2, "apparel.shoes", "brand-c", 80.0, 3, "s3"),
        ("2019-10-01 02:10:00 UTC", "remove_from_cart", 103, 2, "apparel.shoes", "brand-c", 80.0, 3, "s3"),
        ("2019-10-01 03:00:00 UTC", "purchase", 104, 2, "apparel.shoes", "brand-d", 60.0, 4, "s4"),
        ("2019-10-01 03:10:00 UTC", "cart", 104, 2, "apparel.shoes", "brand-d", 60.0, 4, "s4"),
    ]
    return clean_events(spark.createDataFrame(rows, schema=schema)).persist()


def test_cart_recovery_outputs_contract_and_operational_queue(spark):
    cleaned = make_cleaned(spark)
    config = cart_recovery_config({"min_cart_sessions": 2, "min_history_days": 1, "preview_limit": 20})

    _frames, metrics = build_cart_recovery_outputs(
        cleaned,
        config,
        run_id="cart-test",
        input_snapshot={
            "configured_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
        },
    )

    summary = metrics["cart_summary"]
    quality = metrics["cart_quality"]
    product_rows = {str(row["product_id"]): row for row in metrics["cart_product_segments"]}
    category_rows = {row["category_level1"]: row for row in metrics["cart_category_segments"]}

    assert summary["contract_version"] == CART_RECOVERY_CONTRACT_VERSION
    assert summary["cart_product_sessions"] == 4
    assert summary["recovered_sessions"] == 1
    assert summary["abandoned_sessions"] == 3
    assert summary["abandonment_rate"] == 0.75
    assert summary["abandoned_value"] == 190.0
    assert quality["quality_status"] == "passed"

    assert product_rows["101"]["recovered_sessions"] == 1
    assert product_rows["102"]["abandoned_sessions"] == 1
    assert product_rows["103"]["explicit_remove_sessions"] == 1
    assert category_rows["apparel"]["remove_rate"] == 0.5
    assert metrics["cart_recovery_queue"][0]["priority_score"] > 0
    assert any("product_cart_abandonment" in row["reason_codes"] for row in metrics["cart_recovery_queue"])


def test_cart_recovery_quality_flags_sparse_cart_data(spark):
    cleaned = make_cleaned(spark)
    config = cart_recovery_config({"min_cart_sessions": 10, "min_history_days": 3})

    _frames, metrics = build_cart_recovery_outputs(
        cleaned,
        config,
        run_id="cart-quality",
        input_snapshot={"configured_input_path": "input.csv", "actual_input_path": "input.csv"},
    )

    assert metrics["cart_quality"]["quality_status"] == "needs_review"
    assert "low_cart_product_sessions" in metrics["cart_quality"]["warnings"]
    assert "history_days" in metrics["cart_quality"]["warnings"]
