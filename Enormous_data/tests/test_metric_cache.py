from __future__ import annotations

import csv
import json

import pytest

from app.services.metric_cache import CacheNotReadyError, MetricCache
from spark_jobs.dashboard_semantics import DASHBOARD_CUBE_ALL_VALUE, DASHBOARD_CUBE_CONTRACT_VERSION


def test_load_metric(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "summary.json").write_text(json.dumps({"raw_rows": 3}), encoding="utf-8")

    cache = MetricCache(cache_dir, tmp_path / "events.csv")

    assert cache.load_metric("summary") == {"raw_rows": 3}


def test_load_metric_missing(tmp_path):
    cache = MetricCache(tmp_path, tmp_path / "events.csv")

    with pytest.raises(CacheNotReadyError):
        cache.load_metric("summary")


def test_load_table_filters_and_paginates(tmp_path):
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type", "category_code", "brand", "price", "user_session"])
        writer.writeheader()
        writer.writerows(
            [
                {"event_type": "view", "category_code": "electronics.phone", "brand": "apple", "price": "1", "user_session": "s1"},
                {"event_type": "purchase", "category_code": "apparel.shoe", "brand": "apple", "price": "2", "user_session": "s2"},
                {"event_type": "purchase", "category_code": "apparel.shoe", "brand": "samsung", "price": "3", "user_session": "s3"},
            ]
        )

    cache = MetricCache(tmp_path / "cache", raw_path)
    result = cache.load_table(page=1, size=1, event_type="purchase")

    assert result["total"] == 2
    assert result["source_dataset"] == "raw_events_compatible_fallback"
    assert result["rows"][0] == {
        "event_time": "",
        "event_type": "purchase",
        "product_id": "",
        "category_id": "",
        "category_code": "apparel.shoe",
        "category_level1": "apparel",
        "brand": "apple",
        "price": "2",
        "user_id": "",
        "user_session": "s2",
        "source_dataset": "raw_events_compatible_fallback",
    }


def test_load_table_filters_category_and_normalized_brand(tmp_path):
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type", "category_code", "brand", "price", "user_session"])
        writer.writeheader()
        writer.writerows(
            [
                {"event_type": "purchase", "category_code": "electronics.phone", "brand": "apple", "price": "1", "user_session": "s1"},
                {"event_type": "purchase", "category_code": "apparel.shoe", "brand": "", "price": "2", "user_session": ""},
                {"event_type": "view", "category_code": "", "brand": "", "price": "3", "user_session": "s3"},
            ]
        )

    cache = MetricCache(tmp_path / "cache", raw_path)
    result = cache.load_table(page=1, size=10, event_type="purchase", category_level1="apparel", brand="unknown")

    assert result["total"] == 1
    assert result["source_dataset"] == "raw_events_compatible_fallback"
    assert result["rows"][0]["brand"] == "unknown"
    assert result["rows"][0]["category_level1"] == "apparel"
    assert result["rows"][0]["user_session"] == "unknown"


def test_load_table_prefers_cleaned_snapshot_over_raw_csv(tmp_path):
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_time", "event_type", "product_id", "category_id", "category_code", "brand", "price", "user_id", "user_session"])
        writer.writeheader()
        writer.writerow(
            {
                "event_time": "bad",
                "event_type": "purchase",
                "product_id": "raw-product",
                "category_id": "raw-category",
                "category_code": "electronics.phone",
                "brand": "raw-brand",
                "price": "-1",
                "user_id": "raw-user",
                "user_session": "raw-session",
            }
        )
    cache_dir = tmp_path / "cache"
    table_dir = cache_dir / "table_events"
    table_dir.mkdir(parents=True)
    with (table_dir / "part-00000.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "event_time",
                "event_type",
                "product_id",
                "category_id",
                "category_code",
                "category_level1",
                "brand",
                "price",
                "user_id",
                "user_session",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "event_time": "2020-01-01 00:01:00 UTC",
                "event_type": "purchase",
                "product_id": "clean-product",
                "category_id": "11",
                "category_code": "apparel.shoe",
                "category_level1": "apparel",
                "brand": "nike",
                "price": "199.9",
                "user_id": "102",
                "user_session": "s2",
            }
        )

    cache = MetricCache(cache_dir, raw_path)
    result = cache.load_table(page=1, size=10, event_type="purchase", category_level1="apparel", brand="nike")

    assert result["total"] == 1
    assert result["source_dataset"] == "cleaned_events"
    assert result["rows"][0]["product_id"] == "clean-product"
    assert result["rows"][0]["source_dataset"] == "cleaned_events"


def test_load_dashboard_slice_filters_and_returns_evidence(tmp_path):
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["event_time", "event_type", "category_code", "category_level1", "brand", "price", "user_id", "user_session"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "event_time": "2020-01-01 00:00:00 UTC",
                    "event_type": "view",
                    "category_code": "electronics.phone",
                    "category_level1": "electronics",
                    "brand": "apple",
                    "price": "99.9",
                    "user_id": "u1",
                    "user_session": "s1",
                },
                {
                    "event_time": "2020-01-01 00:01:00 UTC",
                    "event_type": "purchase",
                    "category_code": "apparel.shoe",
                    "category_level1": "apparel",
                    "brand": "nike",
                    "price": "199.9",
                    "user_id": "u2",
                    "user_session": "s2",
                },
                {
                    "event_time": "2020-01-02 00:02:00 UTC",
                    "event_type": "purchase",
                    "category_code": "apparel.shoe",
                    "category_level1": "apparel",
                    "brand": "adidas",
                    "price": "299.9",
                    "user_id": "u3",
                    "user_session": "s3",
                },
            ]
        )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": "run-1", "contract_version": "metrics/v1", "elapsed_seconds": 12.3}),
        encoding="utf-8",
    )

    cache = MetricCache(cache_dir, raw_path)
    result = cache.load_dashboard_slice(event_type="purchase", category_level1="apparel", brand="nike")

    assert result["summary"]["event_count"] == 1
    assert result["summary"]["purchase_count"] == 1
    assert result["summary"]["total_sales"] == 199.9
    assert result["event_type_count"] == [{"name": "purchase", "value": 1}]
    assert result["daily_events"] == [{"date": "2020-01-01", "value": 1}]
    assert result["daily_sales"] == [{"date": "2020-01-01", "value": 199.9}]
    assert result["top_categories"] == [{"name": "apparel", "value": 1}]
    assert result["evidence"]["source_dataset"] == "raw_events_compatible_fallback"
    assert result["evidence"]["filtered_row_count"] == 1
    assert result["evidence"]["total_row_count"] == 3
    assert result["evidence"]["coverage_rate"] == pytest.approx(1 / 3)
    assert result["evidence"]["run_id"] == "run-1"
    assert result["evidence"]["dataset_version"] == "run-1:metrics/v1"
    assert result["evidence"]["cache_hit"] is False
    assert result["evidence"]["cache_mode"] == "detail_scan"
    assert result["evidence"]["fallback_reason"] == "dashboard_cube_missing"


def test_load_dashboard_slice_prefers_dashboard_cube_without_raw_csv(tmp_path):
    cache_dir = tmp_path / "cache"
    total_dir = cache_dir / "dashboard_cube_total"
    daily_dir = cache_dir / "dashboard_cube_daily"
    total_dir.mkdir(parents=True)
    daily_dir.mkdir(parents=True)
    fieldnames = [
        "dt",
        "event_type",
        "category_level1",
        "brand",
        "event_count",
        "purchase_count",
        "total_sales",
        "unique_users",
        "unique_sessions",
        "avg_order_value",
        "grain",
        "contract_version",
    ]
    _write_csv_rows(
        total_dir / "part-00000.csv",
        fieldnames,
        [
            {
                "dt": DASHBOARD_CUBE_ALL_VALUE,
                "event_type": DASHBOARD_CUBE_ALL_VALUE,
                "category_level1": DASHBOARD_CUBE_ALL_VALUE,
                "brand": DASHBOARD_CUBE_ALL_VALUE,
                "event_count": "3",
                "purchase_count": "2",
                "total_sales": "499.8",
                "unique_users": "3",
                "unique_sessions": "3",
                "avg_order_value": "249.9",
                "grain": "total",
                "contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
            },
            {
                "dt": DASHBOARD_CUBE_ALL_VALUE,
                "event_type": "purchase",
                "category_level1": "apparel",
                "brand": "nike",
                "event_count": "1",
                "purchase_count": "1",
                "total_sales": "199.9",
                "unique_users": "1",
                "unique_sessions": "1",
                "avg_order_value": "199.9",
                "grain": "total",
                "contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
            },
        ],
    )
    _write_csv_rows(
        daily_dir / "part-00000.csv",
        fieldnames,
        [
            {
                "dt": "2020-01-01",
                "event_type": "purchase",
                "category_level1": "apparel",
                "brand": "nike",
                "event_count": "1",
                "purchase_count": "1",
                "total_sales": "199.9",
                "unique_users": "1",
                "unique_sessions": "1",
                "avg_order_value": "199.9",
                "grain": "daily",
                "contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
            }
        ],
    )
    (cache_dir / "dashboard_semantic_metrics.json").write_text(
        json.dumps(
            [
                {
                    "metric_name": "event_count",
                    "chinese_name": "事件量",
                    "source": "dashboard_metric_cube",
                    "aggregation": "计数",
                    "formula": "符合筛选条件的行为事件行数",
                }
            ]
        ),
        encoding="utf-8",
    )
    (cache_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "cube-run-1",
                "elapsed_seconds": 8.2,
                "output_artifacts": {
                    "dashboard_cube_artifacts": {
                        "total": str(total_dir),
                        "daily": str(daily_dir),
                        "semantic_metrics": str(cache_dir / "dashboard_semantic_metrics.json"),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    cache = MetricCache(cache_dir, tmp_path / "missing-events.csv")
    result = cache.load_dashboard_slice(event_type="purchase", category_level1="apparel", brand="nike")

    assert result["summary"]["event_count"] == 1
    assert result["summary"]["total_sales"] == 199.9
    assert result["event_type_count"] == [{"name": "purchase", "value": 1}]
    assert result["daily_sales"] == [{"date": "2020-01-01", "value": 199.9}]
    assert result["top_categories"] == [{"name": "apparel", "value": 1}]
    assert result["evidence"]["source_dataset"] == "dashboard_metric_cube"
    assert result["evidence"]["cache_mode"] == "spark_cube"
    assert result["evidence"]["cache_hit"] is True
    assert result["evidence"]["fallback_reason"] is None
    assert result["evidence"]["contract_version"] == DASHBOARD_CUBE_CONTRACT_VERSION
    assert result["evidence"]["dataset_version"] == f"cube-run-1:{DASHBOARD_CUBE_CONTRACT_VERSION}"
    assert result["evidence"]["cube_row_count"] == 3
    assert result["evidence"]["metric_definitions"][0]["chinese_name"] == "事件量"


def test_load_dashboard_slice_invalid_event_type_returns_empty_slice(tmp_path):
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_time", "event_type", "category_code", "brand", "price"])
        writer.writeheader()
        writer.writerow(
            {
                "event_time": "2020-01-01 00:00:00 UTC",
                "event_type": "view",
                "category_code": "electronics.phone",
                "brand": "apple",
                "price": "99.9",
            }
        )

    cache = MetricCache(tmp_path / "cache", raw_path)
    result = cache.load_dashboard_slice(event_type="bad")

    assert result["summary"]["event_count"] == 0
    assert result["event_type_count"] == []
    assert result["evidence"]["filtered_row_count"] == 0
    assert result["evidence"]["total_row_count"] == 1
    assert result["evidence"]["cache_hit"] is False


def _write_csv_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
