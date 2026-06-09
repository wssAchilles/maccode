from __future__ import annotations

import csv
import json

import pytest

from app.services.metric_cache import CacheNotReadyError, MetricCache


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
        writer = csv.DictWriter(handle, fieldnames=["event_type", "brand", "price"])
        writer.writeheader()
        writer.writerows(
            [
                {"event_type": "view", "brand": "apple", "price": "1"},
                {"event_type": "purchase", "brand": "apple", "price": "2"},
                {"event_type": "purchase", "brand": "samsung", "price": "3"},
            ]
        )

    cache = MetricCache(tmp_path / "cache", raw_path)
    result = cache.load_table(page=1, size=1, event_type="purchase")

    assert result["total"] == 2
    assert result["rows"] == [{"event_type": "purchase", "brand": "apple", "price": "2"}]
