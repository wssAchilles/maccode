from __future__ import annotations

import json
import os
import sys

import pytest
from pyspark.sql import SparkSession

from app.services.controlled_query import run_controlled_query
from app.services.metric_cache import MetricCache
from spark_jobs.controlled_query import execute_controlled_query_dataframe
from spark_jobs.controlled_query import parse_controlled_query


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("controlled-query-tests")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_parse_controlled_query_recognizes_monthly_sales():
    result = parse_controlled_query("按月份统计销售额")

    assert result.matched is True
    assert result.intent is not None
    assert result.intent.metric == "total_sales"
    assert result.intent.metric_label == "成交额"
    assert result.intent.dimension == "month"
    assert result.intent.dimension_label == "月份"
    assert result.intent.chart_type == "line"


def test_run_controlled_query_aggregates_monthly_sales_from_cache(tmp_path):
    cache = _metric_cache(tmp_path)

    result = run_controlled_query(cache, "按月份统计销售额")

    assert result["matched"] is True
    assert result["chart"]["title"] == "按月份统计成交额"
    assert result["rows"] == [
        {"name": "2020-01", "raw_name": "2020-01", "value": 299.9, "share": 0.60004},
        {"name": "2020-02", "raw_name": "2020-02", "value": 199.9, "share": 0.39996},
    ]
    assert result["evidence"]["row_count"] == 2
    assert result["evidence"]["execution_engine"] == "dashboard_slice_cache"


def test_run_controlled_query_filters_purchase_count_by_category(tmp_path):
    cache = _metric_cache(tmp_path)

    result = run_controlled_query(cache, "按类目统计购买数")

    assert result["matched"] is True
    assert result["intent"]["event_type_filter"] is None
    assert result["rows"][0]["name"] == "apparel"
    assert result["rows"][0]["value"] == 2
    assert "purchase" not in result["message"]


def test_run_controlled_query_uses_brand_sales_metric(tmp_path):
    cache = _metric_cache(tmp_path)

    result = run_controlled_query(cache, "按品牌统计销售额")

    assert result["matched"] is True
    assert result["rows"][:2] == [
        {"name": "nike", "raw_name": "nike", "value": 299.9, "share": 0.60004},
        {"name": "adidas", "raw_name": "adidas", "value": 199.9, "share": 0.39996},
    ]
    assert result["evidence"]["execution_engine"] == "top_brand_metric_cache"


def test_run_controlled_query_returns_unsupported_payload(tmp_path):
    cache = _metric_cache(tmp_path)

    result = run_controlled_query(cache, "帮我找出最值得投资的用户")

    assert result["matched"] is False
    assert result["status"] == "unsupported"
    assert result["rows"] == []
    assert "建议" in "、".join(result["suggestions"]) or result["suggestions"]


def test_execute_controlled_query_dataframe_uses_whitelisted_columns(spark):
    df = spark.createDataFrame(
        [
            {"event_time": "2020-01-01 00:00:00", "event_type": "purchase", "category_level1": "apparel", "brand": "nike", "price": 100.0},
            {"event_time": "2020-01-02 00:00:00", "event_type": "view", "category_level1": "apparel", "brand": "nike", "price": 50.0},
            {"event_time": "2020-02-01 00:00:00", "event_type": "purchase", "category_level1": "electronics", "brand": "sony", "price": 200.0},
        ]
    )
    intent = parse_controlled_query("按月份统计销售额").intent

    rows = execute_controlled_query_dataframe(df, intent)

    assert rows == [{"name": "2020-01", "value": 100.0}, {"name": "2020-02", "value": 200.0}]


def _metric_cache(tmp_path) -> MetricCache:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    raw_path.write_text(
        "\n".join(
            [
                "event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session",
                "2020-01-01 00:00:00 UTC,view,1,10,electronics.phone,apple,99.9,101,s1",
                "2020-01-02 00:00:00 UTC,purchase,2,11,apparel.shoe,nike,299.9,102,s2",
                "2020-02-03 00:00:00 UTC,purchase,3,12,apparel.shoe,adidas,199.9,103,s3",
            ]
        ),
        encoding="utf-8",
    )
    (cache_dir / "top_brands.json").write_text(
        json.dumps(
            [
                {"name": "nike", "orders": 1, "value": 299.9},
                {"name": "adidas", "orders": 1, "value": 199.9},
            ]
        ),
        encoding="utf-8",
    )
    return MetricCache(cache_dir, raw_path)
