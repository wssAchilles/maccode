from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession

from spark_jobs.cleaning import clean_events
from spark_jobs.recommendation import (
    build_product_features,
    build_recommendation_candidates,
    build_recommendation_evaluation,
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


def make_graph_cleaned(spark):
    rows = [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 1, "target-a"),
        ("2019-10-01 00:05:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 2, "co-1"),
        ("2019-10-01 00:06:00 UTC", "view", 301, 3, "accessories.watch", "fitbit", 80.0, 2, "co-1"),
        ("2019-10-01 00:10:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 3, "co-2"),
        ("2019-10-01 00:11:00 UTC", "cart", 301, 3, "accessories.watch", "fitbit", 80.0, 3, "co-2"),
        ("2019-10-01 00:15:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 4, "co-3"),
        ("2019-10-01 00:16:00 UTC", "purchase", 301, 3, "accessories.watch", "fitbit", 80.0, 4, "co-3"),
        ("2019-10-01 00:20:00 UTC", "view", 901, 9, "home.tool", "bosch", 20.0, 5, "noise-1"),
        ("2019-10-01 00:25:00 UTC", "view", 902, 9, "home.tool", "bosch", 22.0, 6, "noise-2"),
        ("2019-10-01 00:30:00 UTC", "view", 903, 9, "home.tool", "bosch", 24.0, 7, "noise-3"),
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


def test_recommendation_evaluation_reports_rule_and_als_baselines(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=5).persist()
    recommendations = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [],
        top_k=3,
        min_confidence=0.01,
    ).persist()

    evaluation = build_recommendation_evaluation(
        cleaned,
        recommendations,
        recommendation_config({"top_k": 3, "evaluation_top_k": 3, "als_min_training_rows": 999}),
        run_id="recommendation-eval",
    )

    assert evaluation["behavior_weights"] == {"view": 1, "cart": 3, "purchase": 8}
    assert {row["model_name"] for row in evaluation["model_metrics"]} == {"rule_recommendation", "als_implicit"}
    assert any(row["status"] == "skipped" and row["model_name"] == "als_implicit" for row in evaluation["model_metrics"])
    assert evaluation["split"]["strategy"] == "leave_latest_interaction_per_session"
    assert evaluation["split"]["rule_candidate_source"] == "train_split_recomputed"
    assert evaluation["split"]["leakage_guard"] == "holdout_pairs_removed_before_candidate_generation"


def test_recommendation_evaluation_recomputes_rule_predictions_from_train_split(spark):
    rows = [
        ("2019-10-01 00:00:00 UTC", "view", 101, 1, "electronics.phone", "apple", 100.0, 1, "s1"),
        ("2019-10-01 00:10:00 UTC", "purchase", 999, 1, "electronics.phone", "sony", 150.0, 1, "s1"),
        ("2019-10-01 00:00:00 UTC", "view", 102, 1, "electronics.phone", "samsung", 90.0, 2, "s2"),
        ("2019-10-01 00:10:00 UTC", "purchase", 998, 1, "electronics.phone", "lg", 120.0, 2, "s2"),
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
    cleaned = clean_events(spark.createDataFrame(rows, schema=schema)).persist()
    leaky_recommendations = spark.createDataFrame(
        [
            {"user_session": "s1", "product_id": "999", "rank": 1, "score": 1.0, "source": "leaky_fixture", "fallback_used": False},
            {"user_session": "s2", "product_id": "998", "rank": 1, "score": 1.0, "source": "leaky_fixture", "fallback_used": False},
        ]
    )

    evaluation = build_recommendation_evaluation(
        cleaned,
        leaky_recommendations,
        recommendation_config(
            {
                "top_k": 1,
                "evaluation_top_k": 1,
                "session_sample_limit": 10,
                "candidate_pool": 10,
                "min_confidence": 0.01,
                "als_min_training_rows": 999,
            }
        ),
        run_id="leakage-guard",
    )

    rule_metrics = next(row for row in evaluation["model_metrics"] if row["model_name"] == "rule_recommendation")
    assert rule_metrics["hit_count"] == 0
    assert rule_metrics["caveat"] == "train_split_recomputed"
    assert evaluation["split"]["production_recommendation_rows"] == 2


def test_graph_neighbor_recall_adds_high_lift_candidates(spark):
    cleaned = make_graph_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=20).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=20).filter("user_session = 'target-a'").persist()

    recommendations = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [],
        top_k=3,
        min_confidence=0.01,
        config=recommendation_config(
            {
                "graph_neighbor_candidate_pool": 10,
                "min_graph_neighbor_support": 2,
                "min_graph_neighbor_lift": 0.5,
            }
        ),
    ).persist()
    rows = [row.asDict() for row in recommendations.collect()]

    graph_row = next(row for row in rows if str(row["product_id"]) == "301")
    assert graph_row["source"] == "graph_neighbor"
    assert graph_row["affinity_score"] > 0
    assert "graph_neighbor_recall" in graph_row["reason_codes"]


def test_recommendation_candidates_explain_recall_and_ranking(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=2).persist()
    recommendations = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [{"product_id": "201"}],
        top_k=3,
        min_confidence=0.01,
    ).persist()

    candidates = build_recommendation_candidates(recommendations, limit=10)

    assert candidates
    assert {"category_recall", "popular_fallback"} & {row["recall_stage"] for row in candidates}
    assert all(row["ranker_model"] == "interpretable_rule_ranker_v1" for row in candidates)
    assert all(0 <= row["ranker_score"] <= 1 for row in candidates)
    assert all(0 <= row["affinity_score"] <= 1 for row in candidates)
    assert all(row["candidate_stage"] == "ranked_topk" for row in candidates)


def test_spark_ml_ranker_scores_candidates_when_training_is_sufficient(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=2).persist()
    recommendations = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [{"product_id": "201"}],
        top_k=3,
        min_confidence=0.01,
        config=recommendation_config({"ranker_min_training_rows": 4, "ranker_max_iter": 3}),
    ).persist()

    rows = [row.asDict() for row in recommendations.collect()]
    candidates = build_recommendation_candidates(recommendations, limit=10)

    assert rows
    assert {row["ranker_model"] for row in rows} == {"spark_ml_logistic_ranker_v1"}
    assert {row["ranker_model"] for row in candidates} == {"spark_ml_logistic_ranker_v1"}
    assert all(0 <= row["score"] <= 1 for row in rows)
    assert all(0 <= row["ranker_score"] <= 1 for row in candidates)


def test_spark_ml_gbt_ranker_can_be_selected(spark):
    cleaned = make_cleaned(spark)
    product_features = build_product_features(cleaned, candidate_pool=10).persist()
    target_sessions = build_target_sessions(cleaned, session_limit=2).persist()
    recommendations = build_recommendation_features(
        cleaned,
        product_features,
        target_sessions,
        [{"product_id": "201"}],
        top_k=3,
        min_confidence=0.01,
        config=recommendation_config(
            {
                "ranker_algorithm": "gbt",
                "ranker_min_training_rows": 4,
                "ranker_max_iter": 3,
                "ranker_max_depth": 2,
            }
        ),
    ).persist()

    rows = [row.asDict() for row in recommendations.collect()]

    assert rows
    assert {row["ranker_model"] for row in rows} == {"spark_ml_gbt_ranker_v1"}
    assert all(0 <= row["score"] <= 1 for row in rows)


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
