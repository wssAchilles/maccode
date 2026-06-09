from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cleaning import clean_events
from spark_jobs.optimization import (
    build_optimization_candidates,
    build_optimization_outputs,
    optimization_config,
    solve_with_greedy,
)


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("optimization-test")
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
        ("2019-10-01 00:10:00 UTC", "purchase", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 01:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 2, "s2"),
        ("2019-10-01 01:10:00 UTC", "purchase", 101, 1, "electronics.phone", "apple", 100.0, 2, "s2"),
        ("2019-10-01 02:00:00 UTC", "view", 102, 2, "apparel.shoes", "nike", 50.0, 3, "s3"),
        ("2019-10-01 02:05:00 UTC", "cart", 102, 2, "apparel.shoes", "nike", 50.0, 3, "s3"),
        ("2019-10-01 02:10:00 UTC", "purchase", 102, 2, "apparel.shoes", "nike", 50.0, 3, "s3"),
        ("2019-10-01 03:00:00 UTC", "view", 103, 2, "apparel.shoes", "nike", 20.0, 4, "s4"),
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


def test_build_optimization_candidates_from_cleaned_events(spark):
    cleaned = make_cleaned(spark)

    _, candidates = build_optimization_candidates(cleaned, candidate_limit=10, global_purchase_rate=0.25)

    first = candidates[0]
    assert first["product_id"] == "101"
    assert first["views"] == 2
    assert first["purchases"] == 2
    assert first["revenue"] == 200.0
    assert first["purchase_rate_shrunk"] > 0
    assert 0 <= first["confidence_weight"] <= 1


def test_greedy_solver_respects_budget_slots_and_caps():
    config = optimization_config(
        {
            "total_budget": 250,
            "slot_count": 1,
            "category_cap": 2,
            "brand_cap": 1,
            "min_views": 1,
            "min_confidence": 0.01,
            "actions": [
                {"name": "feature_slot", "type": "slot", "lift": 0.2, "cost_rate": 0, "fixed_cost": 100},
                {"name": "promo_low", "type": "promo", "lift": 0.1, "cost_rate": 0, "fixed_cost": 80},
            ],
        }
    )
    candidates = [
        _candidate("101", "apple", "electronics", 500),
        _candidate("102", "apple", "electronics", 300),
        _candidate("201", "nike", "apparel", 250),
    ]

    result = solve_with_greedy(candidates, config)
    outputs = build_optimization_outputs(candidates, result, config)

    assert outputs["optimization_summary"]["used_budget"] <= 250
    assert outputs["optimization_summary"]["used_slots"] <= 1
    assert len([row for row in result.selected if row["brand"] == "apple"]) <= 1
    assert outputs["optimization_quality"]["budget_feasible"] is True


def _candidate(product_id: str, brand: str, category: str, baseline_gmv: float):
    return {
        "product_id": product_id,
        "brand": brand,
        "category_level1": category,
        "views": 100,
        "carts": 20,
        "purchases": 10,
        "funnel_purchases": 8,
        "revenue": baseline_gmv,
        "avg_price": 50,
        "view_to_cart_rate": 0.2,
        "cart_to_purchase_rate": 0.4,
        "view_to_purchase_rate": 0.1,
        "revenue_per_view": 5,
        "purchase_rate_shrunk": 0.1,
        "wilson_purchase_rate": 0.05,
        "confidence_weight": 0.8,
        "risk_score": 0.2,
        "baseline_gmv": baseline_gmv,
    }
