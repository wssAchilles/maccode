from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cleaning import clean_events
from spark_jobs.recommendation import (
    build_product_features,
    build_recommendation_features,
    build_recommendation_outputs,
    build_target_sessions,
    evaluate_recommendation_quality_frame,
    evaluate_recommendation_quality,
    recommendation_config,
)


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("recommendation-test")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    yield session
    session.stop()


def make_cleaned(spark):
    rows = [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:05:00 UTC", "cart", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:10:00 UTC", "view", 102, 1, "electronics.phone", "samsung", 90.0, 2, "s2"),
        ("2019-10-01 00:15:00 UTC", "purchase", 102, 1, "electronics.phone", "samsung", 90.0, 2, "s2"),
        ("2019-10-01 00:20:00 UTC", "view", 103, 1, "electronics.phone", "sony", 70.0, 3, "s3"),
        ("2019-10-01 00:25:00 UTC", "cart", 103, 1, "electronics.phone", "sony", 70.0, 3, "s3"),
        ("2019-10-01 00:30:00 UTC", "purchase", 103, 1, "electronics.phone", "sony", 70.0, 3, "s3"),
        ("2019-10-01 01:00:00 UTC", "view", 201, 2, "apparel.shoes", "nike", 50.0, 4, "s4"),
        ("2019-10-01 01:05:00 UTC", "purchase", 201, 2, "apparel.shoes", "nike", 50.0, 4, "s4"),
        ("2019-10-01 02:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 5, "target-a"),
        ("2019-10-01 02:05:00 UTC", "view", 201, 2, "apparel.shoes", "nike", 50.0, 6, "target-b"),
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
    return clean_events(spark.createDataFrame(rows, schema=schema)).persist()


def test_recommendation_ranking_is_deterministic(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=2).persist()

    first = build_recommendation_features(cleaned, product_features, target_sessions, [], top_k=3, min_confidence=0.01).collect()
    second = build_recommendation_features(cleaned, product_features, target_sessions, [], top_k=3, min_confidence=0.01).collect()

    assert [(row["user_session"], row["rank"], row["product_id"]) for row in first] == [
        (row["user_session"], row["rank"], row["product_id"]) for row in second
    ]
    assert len({(row["user_session"], row["product_id"]) for row in first}) == len(first)


def test_recommendation_fallback_fills_sparse_personalization(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=1).persist()

    rows = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [{"product_id": "201"}],
        top_k=3,
        min_confidence=0.99,
    ).collect()

    assert rows
    assert all(row["fallback_used"] for row in rows)
    assert {row["source"] for row in rows} == {"optimization_fallback"}


def test_quality_gate_rejects_high_fallback_rate():
    items = [
        {"user_session": "s1", "product_id": "101", "confidence": 0.5, "fallback_used": True},
        {"user_session": "s1", "product_id": "102", "confidence": 0.5, "fallback_used": True},
    ]
    config = recommendation_config({"max_fallback_rate": 0.2})

    quality = evaluate_recommendation_quality(
        items=items,
        target_session_count=1,
        product_count=2,
        freshness_lag_minutes=1,
        config=config,
    )

    assert quality["passed"] is False
    assert any(check["name"] == "fallback_rate" and not check["passed"] for check in quality["checks"])


def test_quality_gate_uses_spark_aggregation_without_full_item_list(spark):
    features = spark.createDataFrame(
        [
            {"user_session": "s1", "product_id": "101", "confidence": 0.5, "score": 0.7, "fallback_used": False},
            {"user_session": "s1", "product_id": "102", "confidence": 0.4, "score": 0.6, "fallback_used": True},
            {"user_session": "s2", "product_id": "103", "confidence": 0.6, "score": 0.8, "fallback_used": False},
        ]
    )

    quality = evaluate_recommendation_quality_frame(
        recommendation_features=features,
        target_session_count=2,
        product_count=3,
        freshness_lag_minutes=1,
        config=recommendation_config({"min_coverage_rate": 1.0}),
    )

    assert quality["recommendation_count"] == 3
    assert quality["covered_sessions"] == 2
    assert quality["coverage_rate"] == 1.0
    assert quality["fallback_rate"] == pytest.approx(1 / 3)


def test_failed_recommendation_run_keeps_previous_snapshot(spark, tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    previous = [
        {
            "user_session": "previous",
            "user_id": "1",
            "rank": 1,
            "product_id": "999",
            "brand": "old",
            "category_level1": "electronics",
            "score": 0.1,
            "confidence": 0.8,
            "reason_codes": ["previous"],
            "source": "personalized_category",
            "fallback_used": False,
        }
    ]
    (cache_dir / "recommendation_items.json").write_text(__import__("json").dumps(previous), encoding="utf-8")

    _, metrics = build_recommendation_outputs(
        make_cleaned(spark),
        [{"product_id": "201"}],
        recommendation_config({"max_fallback_rate": 0.0, "min_coverage_rate": 1.0}),
        output_dir=cache_dir,
        run_id="failed-run",
        input_snapshot={"actual_input_path": "unit-test"},
    )

    assert metrics["recommendation_quality"]["passed"] is False
    assert metrics["recommendation_summary"]["quality_status"] == "degraded_previous_snapshot"
    assert metrics["recommendation_items"] == previous
