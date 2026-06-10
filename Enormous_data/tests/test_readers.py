from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest
from pyspark.sql import SparkSession

from spark_jobs.readers import read_events


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("readers-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_read_events_supports_parquet_input(spark, tmp_path):
    parquet_path = tmp_path / "events_parquet"
    source = spark.createDataFrame(
        [
            {
                "event_time": "2019-10-01 00:00:00 UTC",
                "event_type": "view",
                "product_id": 1001,
                "category_id": 2001,
                "category_code": "electronics.smartphone",
                "brand": "brand-a",
                "price": 99.9,
                "user_id": 3001,
                "user_session": "s-1",
                "event_timestamp": datetime(2019, 10, 1, 0, 0, 0),
                "event_date": datetime(2019, 10, 1).date(),
                "event_hour": 0,
                "category_level1": "electronics",
            }
        ]
    )
    source.write.mode("overwrite").parquet(str(parquet_path))

    loaded = read_events(spark, str(parquet_path), input_format="parquet")

    assert loaded.count() == 1
    assert loaded.first()["event_type"] == "view"
