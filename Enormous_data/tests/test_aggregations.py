from __future__ import annotations

import os
import sys
from datetime import date, datetime

import pytest
from pyspark.sql import SparkSession

from spark_jobs.aggregations import daily_events, daily_sales


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("aggregations-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_daily_events_switches_to_intraday_axis_for_single_day(spark):
    df = spark.createDataFrame(
        [
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 0,
                "event_timestamp": datetime(2019, 11, 1, 0, 1),
                "event_type": "view",
                "price": 10.0,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 0,
                "event_timestamp": datetime(2019, 11, 1, 0, 12),
                "event_type": "cart",
                "price": 10.0,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 0,
                "event_timestamp": datetime(2019, 11, 1, 0, 31),
                "event_type": "view",
                "price": 15.0,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 9,
                "event_timestamp": datetime(2019, 11, 1, 9, 44),
                "event_type": "view",
                "price": 20.0,
            },
        ]
    )

    assert daily_events(df) == [
        {"date": "2019-11-01 00:00", "value": 1},
        {"date": "2019-11-01 00:10", "value": 1},
        {"date": "2019-11-01 00:30", "value": 1},
        {"date": "2019-11-01 09:40", "value": 1},
    ]


def test_daily_sales_switches_to_intraday_axis_for_single_purchase_day(spark):
    df = spark.createDataFrame(
        [
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 0,
                "event_timestamp": datetime(2019, 11, 1, 0, 0),
                "event_type": "view",
                "price": 10.0,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 1,
                "event_timestamp": datetime(2019, 11, 1, 1, 4),
                "event_type": "purchase",
                "price": 10.25,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 1,
                "event_timestamp": datetime(2019, 11, 1, 1, 14),
                "event_type": "purchase",
                "price": 15.25,
            },
            {
                "event_date": date(2019, 11, 1),
                "event_hour": 7,
                "event_timestamp": datetime(2019, 11, 1, 7, 46),
                "event_type": "purchase",
                "price": 20.0,
            },
        ]
    )

    assert daily_sales(df) == [
        {"date": "2019-11-01 01:00", "value": 10.25},
        {"date": "2019-11-01 01:10", "value": 15.25},
        {"date": "2019-11-01 07:40", "value": 20.0},
    ]


def test_daily_events_keeps_date_axis_for_multi_day_data(spark):
    df = spark.createDataFrame(
        [
            {"event_date": date(2019, 11, 1), "event_hour": 0, "event_type": "view", "price": 10.0},
            {"event_date": date(2019, 11, 2), "event_hour": 0, "event_type": "view", "price": 15.0},
            {"event_date": date(2019, 11, 2), "event_hour": 1, "event_type": "cart", "price": 20.0},
        ]
    )

    assert daily_events(df) == [
        {"date": "2019-11-01", "value": 1},
        {"date": "2019-11-02", "value": 2},
    ]
