from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class CacheNotReadyError(RuntimeError):
    pass


class MetricCache:
    def __init__(self, cache_dir: str | Path, raw_data_path: str | Path):
        self.cache_dir = Path(cache_dir)
        self.raw_data_path = Path(raw_data_path)

    def load_metric(self, name: str) -> Any:
        path = self.cache_dir / f"{name}.json"
        if not path.exists():
            raise CacheNotReadyError(f"metric cache not found: {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_table(
        self,
        page: int = 1,
        size: int = 20,
        event_type: str | None = None,
        brand: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be greater than 0")
        if size < 1 or size > 100:
            raise ValueError("size must be between 1 and 100")
        if not self.raw_data_path.exists():
            raise CacheNotReadyError(f"raw data not found: {self.raw_data_path.name}")

        rows: list[dict[str, str]] = []
        total = 0
        start = (page - 1) * size
        end = start + size

        with self.raw_data_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if event_type and row.get("event_type") != event_type:
                    continue
                if brand and row.get("brand") != brand:
                    continue

                if start <= total < end:
                    rows.append(row)
                total += 1

        return {
            "page": page,
            "size": size,
            "total": total,
            "rows": rows,
        }
