from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.experimentation import EXPERIMENT_CONTRACT_VERSION, build_experiment_outputs, experiment_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("experimentation-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_experimentation_outputs_assign_holdouts_and_guardrails(spark):
    user_lifecycle = spark.createDataFrame(
        [
            {
                "user_id": f"u{idx}",
                "lifecycle_segment": "high_value" if idx % 3 == 0 else "cart_intent",
                "risk_band": "active_value" if idx % 3 == 0 else "convert_intent",
                "preferred_category_level1": "electronics" if idx % 2 == 0 else "apparel",
                "sessions": 2,
                "views": 10 + idx,
                "carts": 2,
                "purchases": 1 if idx % 3 == 0 else 0,
                "revenue": 300.0 if idx % 3 == 0 else 0.0,
                "avg_order_value": 300.0 if idx % 3 == 0 else None,
            }
            for idx in range(1, 13)
        ]
    )
    recommendation_features = spark.createDataFrame(
        [
            {
                "user_session": f"s{idx}",
                "user_id": f"u{idx}",
                "rank": 1,
                "product_id": f"p{idx}",
                "brand": "brand",
                "category_level1": "electronics",
                "score": 0.2,
                "confidence": 0.2,
                "reason_codes": ["category_affinity"],
                "source": "personalized_category",
                "fallback_used": False,
            }
            for idx in range(1, 7)
        ]
    )
    optimization_plan = [
        {"product_id": "p1", "category_level1": "electronics", "expected_incremental_gmv": 120.0},
        {"product_id": "p2", "category_level1": "apparel", "expected_incremental_gmv": 80.0},
    ]

    frames, metrics = build_experiment_outputs(
        user_lifecycle,
        recommendation_features,
        optimization_plan,
        experiment_config(
            {
                "preview_limit": 20,
                "min_assignment_users": 4,
                "min_treatment_users": 2,
                "min_control_users": 2,
                "max_segment_imbalance": 0.8,
            }
        ),
        run_id="experiment-test",
    )

    assert metrics["experiment_summary"]["contract_version"] == EXPERIMENT_CONTRACT_VERSION
    assert metrics["experiment_summary"]["experiment_count"] == 3
    assert metrics["experiment_summary"]["assignment_rows"] > 0
    assert metrics["experiment_summary"]["assigned_users"] == 12
    assert metrics["experiment_summary"]["expected_incremental_gmv"] > 0
    assert metrics["experiment_guardrails"]["status"] == "passed"
    assert metrics["experiment_results"]
    assert metrics["experiment_results"][0]["measurement_status"] == "offline_history_replay"
    assert "srm_p_value" in metrics["experiment_results"][0]
    assert metrics["experiment_uplift"]["causal_valid"] is False
    assert metrics["experiment_uplift"]["deciles"]
    assert any(row["experiment_key"] == "lifecycle_reactivation" for row in metrics["experiment_assignments"])
    assert any(row["variant"] == "treatment" for row in metrics["experiment_assignments"])
    assert any(row["variant"] == "control" for row in metrics["experiment_assignments"])
    assert frames["experiment_assignments"].count() == metrics["experiment_summary"]["assignment_rows"]


def test_experimentation_preview_limit_keeps_summary_statistics(spark):
    user_lifecycle = spark.createDataFrame(
        [
            {
                "user_id": f"u{idx}",
                "lifecycle_segment": "high_value",
                "risk_band": "convert_intent",
                "preferred_category_level1": "electronics",
                "sessions": 2,
                "views": 10,
                "carts": 1,
                "purchases": 1,
                "revenue": 100.0,
                "avg_order_value": 100.0,
            }
            for idx in range(10)
        ]
    )
    recommendation_features = spark.createDataFrame(
        [
            {
                "user_session": "s1",
                "rank": 1,
                "product_id": "p1",
                "fallback_used": False,
                "confidence": 0.2,
            }
        ]
    )

    frames, metrics = build_experiment_outputs(
        user_lifecycle,
        recommendation_features,
        [],
        experiment_config({"preview_limit": 2, "min_assignment_users": 1, "min_treatment_users": 1, "min_control_users": 1}),
        run_id="experiment-preview",
    )

    assert len(metrics["experiment_assignments"]) == 2
    assert len(metrics["experiment_segments"]) <= 2
    assert frames["experiment_assignments"].count() == metrics["experiment_summary"]["assignment_rows"]
    assert metrics["experiment_summary"]["assignment_rows"] > len(metrics["experiment_assignments"])
    assert metrics["experiment_results"]
    assert metrics["experiment_uplift"]["measurement_status"] == "offline_history_replay"
