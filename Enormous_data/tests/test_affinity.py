from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.affinity import AFFINITY_CONTRACT_VERSION, affinity_config, build_affinity_outputs


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("affinity-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_affinity_outputs_edges_opportunities_and_quality(spark):
    rows = [
        {"event_time": "2020-01-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s1"},
        {"event_time": "2020-01-01 00:01:00", "event_type": "view", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s1"},
        {"event_time": "2020-01-01 00:02:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s1"},
        {"event_time": "2020-01-01 00:03:00", "event_type": "purchase", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s1"},
        {"event_time": "2020-01-02 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s2"},
        {"event_time": "2020-01-02 00:01:00", "event_type": "view", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s2"},
        {"event_time": "2020-01-02 00:02:00", "event_type": "cart", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s2"},
        {"event_time": "2020-01-02 00:03:00", "event_type": "cart", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s2"},
        {"event_time": "2020-01-02 00:04:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s2"},
        {"event_time": "2020-01-02 00:05:00", "event_type": "purchase", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s2"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_affinity_outputs(
        df,
        affinity_config({"min_support": 2, "min_eligible_sessions": 2, "preview_limit": 20}),
        run_id="affinity-test",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
    )

    summary = metrics["affinity_summary"]
    assert summary["contract_version"] == AFFINITY_CONTRACT_VERSION
    assert summary["quality_status"] == "passed"
    assert summary["edge_count"] >= 2
    assert summary["opportunity_count"] >= 1
    assert any(row["relation_type"] == "co_purchase" and row["support"] == 2 for row in metrics["affinity_edges"])
    assert any(row["type"] == "bundle" for row in metrics["affinity_opportunities"])
    assert metrics["affinity_quality"]["sparse_graph"] is False
    assert metrics["affinity_quality"]["pair_base_rows"] >= 1
    assert metrics["affinity_quality"]["pair_rows_per_input_row"] > 0
    assert metrics["affinity_quality"]["pair_rows_per_product_session"] > 0
    assert any(check["name"] == "pair_rows_per_input_row" for check in metrics["affinity_quality"]["checks"])
    assert summary["pair_rows_per_input_row"] == metrics["affinity_quality"]["pair_rows_per_input_row"]
    assert frames["edges"].count() >= 2
    assert metrics["affinity_centrality"]
    assert metrics["affinity_centrality"][0]["pagerank_score"] >= 0
    assert metrics["affinity_centrality"][0]["centrality_score"] >= 0
    assert frames["centrality"].count() >= 1


def test_affinity_sparse_graph_needs_review(spark):
    rows = [
        {"event_time": "2020-01-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "brand": "samsung", "price": 100.0, "user_session": "s1"},
        {"event_time": "2020-01-01 00:01:00", "event_type": "view", "product_id": 2, "category_level1": "electronics", "brand": "sony", "price": 200.0, "user_session": "s1"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_affinity_outputs(
        df,
        affinity_config({"min_support": 3, "min_eligible_sessions": 5}),
        run_id="affinity-sparse",
        input_snapshot={},
    )

    assert metrics["affinity_summary"]["quality_status"] == "needs_review"
    assert metrics["affinity_quality"]["sparse_graph"] is True
    assert metrics["affinity_edges"] == []
