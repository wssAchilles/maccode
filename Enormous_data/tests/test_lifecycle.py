from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.lifecycle import LIFECYCLE_CONTRACT_VERSION, build_lifecycle_outputs, lifecycle_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("lifecycle-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_lifecycle_outputs_segment_users_and_risk_queue(spark):
    daily_user = spark.createDataFrame(
        [
            {"dt": "2019-10-01", "user_id": "u1", "sessions": 1, "views": 10, "carts": 2, "purchases": 1, "revenue": 600.0, "active_minutes": 10.0, "distinct_products": 3, "distinct_categories": 1, "preferred_category_level1": "electronics"},
            {"dt": "2019-10-02", "user_id": "u1", "sessions": 2, "views": 12, "carts": 2, "purchases": 1, "revenue": 700.0, "active_minutes": 15.0, "distinct_products": 4, "distinct_categories": 1, "preferred_category_level1": "electronics"},
            {"dt": "2019-10-02", "user_id": "u2", "sessions": 1, "views": 8, "carts": 3, "purchases": 0, "revenue": 0.0, "active_minutes": 8.0, "distinct_products": 2, "distinct_categories": 1, "preferred_category_level1": "apparel"},
            {"dt": "2019-10-01", "user_id": "u3", "sessions": 1, "views": 4, "carts": 0, "purchases": 0, "revenue": 0.0, "active_minutes": 4.0, "distinct_products": 1, "distinct_categories": 1, "preferred_category_level1": "electronics"},
        ]
    )
    daily_category = spark.createDataFrame(
        [
            {"dt": "2019-10-02", "category_level1": "electronics", "views": 100, "carts": 10, "purchases": 3, "unique_users": 80, "revenue": 1300.0, "avg_price": 433.3, "conversion_rate": 0.03},
            {"dt": "2019-10-02", "category_level1": "apparel", "views": 40, "carts": 5, "purchases": 1, "unique_users": 30, "revenue": 120.0, "avg_price": 120.0, "conversion_rate": 0.025},
        ]
    )

    _, metrics = build_lifecycle_outputs(
        daily_user,
        daily_category,
        lifecycle_config({"high_value_revenue": 500, "champion_min_revenue": 1000, "champion_min_purchase_days": 2}),
        run_id="lifecycle-test",
    )

    assert metrics["lifecycle_summary"]["contract_version"] == LIFECYCLE_CONTRACT_VERSION
    assert metrics["lifecycle_summary"]["user_count"] == 3
    assert metrics["lifecycle_summary"]["high_value_users"] == 1
    assert any(row["lifecycle_segment"] == "champion" for row in metrics["lifecycle_risk_queue"])
    assert any(row["risk_band"] == "convert_intent" for row in metrics["lifecycle_risk_queue"])
    assert metrics["lifecycle_category_affinity"][0]["category_level1"] == "electronics"
    assert metrics["lifecycle_rules"]["model"].startswith("deterministic RFM")
