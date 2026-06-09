from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cleaning import clean_events
from spark_jobs.conversion import (
    build_conversion_quality,
    build_session_facts,
    daily_conversion,
    product_conversion,
    session_funnel,
)


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("conversion-metrics-test")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    yield session
    session.stop()


def ecommerce_rows():
    return [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 00:05:00 UTC", "cart", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 00:10:00 UTC", "purchase", 101, 1, "electronics.phone", "brand-a", 100.0, 1, "s1"),
        ("2019-10-01 01:00:00 UTC", "view", 102, 1, "electronics.phone", "brand-b", 50.0, 2, "s2"),
        ("2019-10-01 01:03:00 UTC", "cart", 102, 1, "electronics.phone", "brand-b", 50.0, 2, "s2"),
        ("2019-10-01 02:00:00 UTC", "view", 103, 2, "apparel.shoes", "brand-c", 80.0, 3, "s3"),
        ("2019-10-01 03:00:00 UTC", "purchase", 104, 3, "unknown", "brand-d", None, 4, "s4"),
        ("2019-10-01 03:05:00 UTC", "view", 104, 3, "unknown", "brand-d", None, 4, "s4"),
    ]


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
    return clean_events(spark.createDataFrame(ecommerce_rows(), schema=schema)).persist()


def test_session_funnel_counts_rates_and_revenue(spark):
    cleaned = make_cleaned(spark)
    session_facts = build_session_facts(cleaned).persist()

    funnel = session_funnel(session_facts)

    assert funnel["totals"]["sessions"] == 4
    assert funnel["totals"]["view_sessions"] == 4
    assert funnel["totals"]["cart_sessions"] == 2
    assert funnel["totals"]["purchase_sessions"] == 1
    assert funnel["totals"]["view_to_cart_rate"] == 0.5
    assert funnel["totals"]["cart_to_purchase_rate"] == 0.5
    assert funnel["totals"]["view_to_purchase_rate"] == 0.25
    assert funnel["totals"]["revenue"] == 100.0
    assert funnel["steps"][2]["step"] == "purchase"


def test_conversion_quality_tracks_ordering_and_missing_price(spark):
    cleaned = make_cleaned(spark)
    session_facts = build_session_facts(cleaned).persist()

    quality = build_conversion_quality(cleaned, session_facts)

    assert quality["session_fact_rows"] == 4
    assert quality["ordering_anomaly_sessions"] == 1
    assert quality["ordering_anomaly_ratio"] == 0.25
    assert quality["purchase_missing_price_rows"] == 1
    assert quality["purchase_missing_price_ratio"] == 0.5


def test_daily_and_product_conversion_outputs_are_stable(spark):
    cleaned = make_cleaned(spark)
    session_facts = build_session_facts(cleaned).persist()

    daily = daily_conversion(session_facts)
    products = product_conversion(cleaned, 2)

    assert daily == [
        {
            "date": "2019-10-01 08:00",
            "sessions": 1,
            "purchase_sessions": 1,
            "view_to_purchase_rate": 1.0,
            "revenue": 100.0,
        },
        {
            "date": "2019-10-01 09:00",
            "sessions": 1,
            "purchase_sessions": 0,
            "view_to_purchase_rate": 0.0,
            "revenue": 0.0,
        },
        {
            "date": "2019-10-01 10:00",
            "sessions": 1,
            "purchase_sessions": 0,
            "view_to_purchase_rate": 0.0,
            "revenue": 0.0,
        },
        {
            "date": "2019-10-01 11:00",
            "sessions": 1,
            "purchase_sessions": 0,
            "view_to_purchase_rate": 0.0,
            "revenue": 0.0,
        }
    ]
    assert products[0]["product_id"] == "101"
    assert products[0]["views"] == 1
    assert products[0]["carts"] == 1
    assert products[0]["purchases"] == 1
    assert products[0]["view_to_cart_rate"] == 1.0
