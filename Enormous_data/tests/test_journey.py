from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.journey import JOURNEY_CONTRACT_VERSION, build_journey_outputs, journey_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("journey-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_journey_outputs_paths_transitions_and_exit_events(spark):
    rows = [
        {"event_time": "2019-11-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:01:00", "event_type": "cart", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:02:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:03:00", "event_type": "view", "product_id": 2, "category_level1": "apparel", "price": 50.0, "user_id": 11, "user_session": "s2"},
        {"event_time": "2019-11-01 00:04:00", "event_type": "cart", "product_id": 2, "category_level1": "apparel", "price": 50.0, "user_id": 11, "user_session": "s2"},
        {"event_time": "2019-11-01 00:05:00", "event_type": "remove_from_cart", "product_id": 2, "category_level1": "apparel", "price": 50.0, "user_id": 11, "user_session": "s2"},
        {"event_time": "2019-11-01 00:06:00", "event_type": "view", "product_id": 3, "category_level1": "apparel", "price": 40.0, "user_id": 12, "user_session": "s3"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_journey_outputs(df, journey_config({"preview_limit": 20}), run_id="journey-test")

    assert metrics["journey_summary"]["contract_version"] == JOURNEY_CONTRACT_VERSION
    assert metrics["journey_summary"]["sessions"] == 3
    assert metrics["journey_summary"]["purchase_sessions"] == 1
    assert any(row["path_signature"] == "view → cart → purchase" for row in metrics["journey_paths"])
    assert any(row["from_event"] == "cart" and row["to_event"] == "purchase" for row in metrics["journey_transitions"])
    assert any(row["last_event"] == "remove_from_cart" for row in metrics["journey_exit_events"])
    assert metrics["journey_purchase_paths"][0]["path_signature"] == "view → cart → purchase"
    assert frames["session_paths"].count() == 3
