from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spark_jobs.dashboard_semantics import (
    DASHBOARD_CUBE_ALL_VALUE,
    DASHBOARD_CUBE_CONTRACT_VERSION,
    DASHBOARD_SEMANTIC_VERSION,
    dashboard_metric_definitions,
)

EVENT_TYPES = {"view", "cart", "remove_from_cart", "purchase"}
TABLE_COLUMNS = [
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
]
CLEANED_TABLE_SOURCE = "cleaned_events"
RAW_FALLBACK_TABLE_SOURCE = "raw_events_compatible_fallback"
DASHBOARD_CUBE_SOURCE = "dashboard_metric_cube"
DASHBOARD_CUBE_MODE = "spark_cube"
DETAIL_SCAN_MODE = "detail_scan"
DASHBOARD_CUBE_MISSING_REASON = "dashboard_cube_missing"
DASHBOARD_CUBE_UNREADABLE_REASON = "dashboard_cube_unreadable"
DASHBOARD_CUBE_DIMENSIONS = ("event_type", "category_level1", "brand")


class CacheNotReadyError(RuntimeError):
    pass


def _normalized_text(value: Any, fallback: str = "unknown") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _category_level1(category_code: str) -> str:
    return _normalized_text(category_code.split(".", 1)[0])


def _normalized_table_row(row: dict[str, str], source_dataset: str) -> dict[str, str]:
    category_code = _normalized_text(row.get("category_code"))
    category_level1 = _normalized_text(row.get("category_level1"), "")
    normalized = {column: _normalized_text(row.get(column), "") for column in TABLE_COLUMNS}
    normalized["brand"] = _normalized_text(row.get("brand"))
    normalized["category_code"] = category_code
    normalized["category_level1"] = category_level1 or _category_level1(category_code)
    normalized["user_session"] = _normalized_text(row.get("user_session"))
    normalized["source_dataset"] = source_dataset
    return normalized


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    return int(_safe_float(value))


def _event_date(event_time: str) -> str:
    text = _normalized_text(event_time, "")
    if len(text) >= 10:
        return text[:10]
    return "unknown"


class MetricCache:
    def __init__(self, cache_dir: str | Path, raw_data_path: str | Path, cleaned_table_path: str | Path | None = None):
        self.cache_dir = Path(cache_dir)
        self.raw_data_path = Path(raw_data_path)
        self.cleaned_table_path = Path(cleaned_table_path) if cleaned_table_path else None

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
        category_level1: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be greater than 0")
        if size < 1 or size > 100:
            raise ValueError("size must be between 1 and 100")
        csv_paths, source_dataset = self._table_source()
        if event_type and event_type not in EVENT_TYPES:
            return {
                "page": page,
                "size": size,
                "total": 0,
                "source_dataset": source_dataset,
                "rows": [],
            }

        rows: list[dict[str, str]] = []
        total = 0
        start = (page - 1) * size
        end = start + size
        normalized_brand = _normalized_text(brand, "") if brand else None
        normalized_category = _normalized_text(category_level1, "") if category_level1 else None

        for normalized in self._iter_table_rows(csv_paths, source_dataset):
            if not self._matches_filters(normalized, event_type, normalized_brand, normalized_category):
                continue

            if start <= total < end:
                rows.append(normalized)
            total += 1

        return {
            "page": page,
            "size": size,
            "total": total,
            "source_dataset": source_dataset,
            "rows": rows,
        }

    def load_dashboard_slice(
        self,
        event_type: str | None = None,
        brand: str | None = None,
        category_level1: str | None = None,
    ) -> dict[str, Any]:
        cube_slice = self._load_dashboard_slice_from_cube(
            event_type=event_type,
            brand=brand,
            category_level1=category_level1,
        )
        if cube_slice is not None:
            return cube_slice

        return self._load_dashboard_slice_from_table(
            event_type=event_type,
            brand=brand,
            category_level1=category_level1,
            fallback_reason=DASHBOARD_CUBE_MISSING_REASON,
        )

    def _load_dashboard_slice_from_table(
        self,
        event_type: str | None = None,
        brand: str | None = None,
        category_level1: str | None = None,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        csv_paths, source_dataset = self._table_source()
        normalized_brand = _normalized_text(brand, "") if brand else None
        normalized_category = _normalized_text(category_level1, "") if category_level1 else None
        event_filter = event_type if event_type in EVENT_TYPES else None
        invalid_event_type = bool(event_type and event_type not in EVENT_TYPES)

        total_row_count = 0
        filtered_row_count = 0
        purchase_count = 0
        total_sales = 0.0
        unique_users: set[str] = set()
        unique_sessions: set[str] = set()
        event_counts: dict[str, int] = defaultdict(int)
        daily_events: dict[str, int] = defaultdict(int)
        daily_sales: dict[str, float] = defaultdict(float)
        category_counts: dict[str, int] = defaultdict(int)

        for normalized in self._iter_table_rows(csv_paths, source_dataset):
            total_row_count += 1
            if invalid_event_type:
                continue
            if not self._matches_filters(normalized, event_filter, normalized_brand, normalized_category):
                continue

            filtered_row_count += 1
            current_event_type = _normalized_text(normalized.get("event_type"))
            event_counts[current_event_type] += 1
            daily_events[_event_date(normalized.get("event_time", ""))] += 1
            category_counts[_normalized_text(normalized.get("category_level1"))] += 1

            user_id = _normalized_text(normalized.get("user_id"), "")
            user_session = _normalized_text(normalized.get("user_session"), "")
            if user_id:
                unique_users.add(user_id)
            if user_session:
                unique_sessions.add(user_session)

            if current_event_type == "purchase":
                purchase_count += 1
                price = _safe_float(normalized.get("price"))
                total_sales += price
                daily_sales[_event_date(normalized.get("event_time", ""))] += price

        evidence = self._dashboard_slice_evidence(
            source_dataset=source_dataset,
            filtered_row_count=filtered_row_count,
            total_row_count=total_row_count,
            query_ms=(time.perf_counter() - started) * 1000,
            filters={
                "event_type": event_type,
                "category_level1": category_level1,
                "brand": brand,
            },
            cache_mode=DETAIL_SCAN_MODE,
            cache_hit=False,
            fallback_reason=fallback_reason,
            semantic_version=DASHBOARD_SEMANTIC_VERSION,
            metric_grain="明细事件扫描",
            metric_definitions=self._dashboard_metric_definitions(),
        )
        return {
            "summary": {
                "event_count": filtered_row_count,
                "purchase_count": purchase_count,
                "total_sales": round(total_sales, 2),
                "unique_users": len(unique_users),
                "unique_sessions": len(unique_sessions),
                "avg_order_value": round(total_sales / purchase_count, 2) if purchase_count else 0,
            },
            "event_type_count": self._named_values(event_counts),
            "daily_events": self._date_values(daily_events),
            "daily_sales": self._date_values(daily_sales, round_values=True),
            "top_categories": self._named_values(category_counts, limit=12),
            "evidence": evidence,
        }

    def _load_dashboard_slice_from_cube(
        self,
        event_type: str | None = None,
        brand: str | None = None,
        category_level1: str | None = None,
    ) -> dict[str, Any] | None:
        sources = self._dashboard_cube_sources()
        if sources is None:
            return None

        started = time.perf_counter()
        (total_csv_paths, total_source_path), (daily_csv_paths, daily_source_path) = sources
        normalized_brand = _normalized_text(brand, "") if brand else None
        normalized_category = _normalized_text(category_level1, "") if category_level1 else None
        event_filter = event_type if event_type in EVENT_TYPES else None
        invalid_event_type = bool(event_type and event_type not in EVENT_TYPES)
        filters = {
            "event_type": event_filter,
            "category_level1": normalized_category,
            "brand": normalized_brand,
        }

        try:
            total_rows = list(self._iter_dashboard_cube_rows(total_csv_paths))
            daily_rows = list(self._iter_dashboard_cube_rows(daily_csv_paths))
        except (OSError, csv.Error, ValueError):
            return self._load_dashboard_slice_from_table(
                event_type=event_type,
                brand=brand,
                category_level1=category_level1,
                fallback_reason=DASHBOARD_CUBE_UNREADABLE_REASON,
            )

        all_summary = self._find_cube_row(total_rows, {"event_type": None, "category_level1": None, "brand": None})
        summary_row = None if invalid_event_type else self._find_cube_row(total_rows, filters)
        total_row_count = _safe_int((all_summary or {}).get("event_count"))
        filtered_row_count = _safe_int((summary_row or {}).get("event_count"))
        purchase_count = _safe_int((summary_row or {}).get("purchase_count"))
        total_sales = _safe_float((summary_row or {}).get("total_sales"))
        evidence = self._dashboard_slice_evidence(
            source_dataset=DASHBOARD_CUBE_SOURCE,
            filtered_row_count=filtered_row_count,
            total_row_count=total_row_count,
            query_ms=(time.perf_counter() - started) * 1000,
            filters={
                "event_type": event_type,
                "category_level1": category_level1,
                "brand": brand,
            },
            cache_mode=DASHBOARD_CUBE_MODE,
            cache_hit=True,
            cube_path=str(total_source_path),
            cube_paths={"total": str(total_source_path), "daily": str(daily_source_path)},
            cube_row_count=len(total_rows) + len(daily_rows),
            contract_version=DASHBOARD_CUBE_CONTRACT_VERSION,
            semantic_version=DASHBOARD_SEMANTIC_VERSION,
            metric_grain="筛选维度汇总 / 日级趋势",
            metric_definitions=self._dashboard_metric_definitions(),
        )
        if invalid_event_type:
            return self._empty_dashboard_slice(evidence)

        return {
            "summary": {
                "event_count": filtered_row_count,
                "purchase_count": purchase_count,
                "total_sales": round(total_sales, 2),
                "unique_users": _safe_int((summary_row or {}).get("unique_users")),
                "unique_sessions": _safe_int((summary_row or {}).get("unique_sessions")),
                "avg_order_value": _safe_float((summary_row or {}).get("avg_order_value")),
            },
            "event_type_count": self._cube_named_values(total_rows, filters, "event_type", "event_count"),
            "daily_events": self._cube_date_values(daily_rows, filters, "event_count"),
            "daily_sales": self._cube_date_values(daily_rows, filters, "total_sales", round_values=True),
            "top_categories": self._cube_named_values(total_rows, filters, "category_level1", "event_count", limit=12),
            "evidence": evidence,
        }

    @staticmethod
    def _empty_dashboard_slice(evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": {
                "event_count": 0,
                "purchase_count": 0,
                "total_sales": 0,
                "unique_users": 0,
                "unique_sessions": 0,
                "avg_order_value": 0,
            },
            "event_type_count": [],
            "daily_events": [],
            "daily_sales": [],
            "top_categories": [],
            "evidence": evidence,
        }

    def _table_source(self) -> tuple[list[Path], str]:
        for path in self._cleaned_table_candidates():
            csv_paths = self._csv_paths(path)
            if csv_paths:
                return csv_paths, CLEANED_TABLE_SOURCE
        if not self.raw_data_path.exists():
            raise CacheNotReadyError(f"raw data not found: {self.raw_data_path.name}")
        return [self.raw_data_path], RAW_FALLBACK_TABLE_SOURCE

    def _dashboard_cube_sources(self) -> tuple[tuple[list[Path], Path], tuple[list[Path], Path]] | None:
        total_source = self._dashboard_cube_source("total")
        daily_source = self._dashboard_cube_source("daily")
        if not total_source or not daily_source:
            return None
        return total_source, daily_source

    def _dashboard_cube_source(self, grain: str) -> tuple[list[Path], Path] | None:
        for path in self._dashboard_cube_candidates(grain):
            csv_paths = self._csv_paths(path)
            if csv_paths:
                return csv_paths, path
        return None

    def _dashboard_cube_candidates(self, grain: str) -> list[Path]:
        candidates: list[Path] = []
        manifest = self._load_run_manifest()
        artifacts = manifest.get("output_artifacts", {}) if isinstance(manifest, dict) else {}
        cube_artifacts = artifacts.get("dashboard_cube_artifacts") or artifacts.get("dashboard_cube") or {}
        if isinstance(cube_artifacts, dict) and cube_artifacts.get(grain):
            candidates.extend(self._resolve_relative_path(str(cube_artifacts[grain])))
        direct_artifact = artifacts.get(f"dashboard_cube_{grain}")
        if direct_artifact:
            candidates.extend(self._resolve_relative_path(str(direct_artifact)))

        candidates.extend([self.cache_dir / f"dashboard_cube_{grain}", self.cache_dir / f"dashboard_cube_{grain}.csv"])
        return self._dedupe_paths(candidates)

    def _iter_dashboard_cube_rows(self, csv_paths: list[Path]):
        for path in csv_paths:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    yield {
                        "dt": _normalized_text(row.get("dt")),
                        "event_type": _normalized_text(row.get("event_type")),
                        "category_level1": _normalized_text(row.get("category_level1")),
                        "brand": _normalized_text(row.get("brand")),
                        "event_count": _safe_int(row.get("event_count")),
                        "purchase_count": _safe_int(row.get("purchase_count")),
                        "total_sales": _safe_float(row.get("total_sales")),
                        "unique_users": _safe_int(row.get("unique_users")),
                        "unique_sessions": _safe_int(row.get("unique_sessions")),
                        "avg_order_value": _safe_float(row.get("avg_order_value")),
                        "grain": _normalized_text(row.get("grain"), ""),
                        "contract_version": _normalized_text(row.get("contract_version"), DASHBOARD_CUBE_CONTRACT_VERSION),
                    }

    def _find_cube_row(self, rows: list[dict[str, Any]], filters: dict[str, str | None]) -> dict[str, Any] | None:
        return next((row for row in rows if self._cube_row_matches_filters(row, filters)), None)

    def _cube_named_values(
        self,
        rows: list[dict[str, Any]],
        filters: dict[str, str | None],
        dimension: str,
        metric: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        values: dict[str, int] = defaultdict(int)
        for row in rows:
            if not self._cube_row_matches_filters(row, filters, expansion_dimension=dimension):
                continue
            values[_normalized_text(row.get(dimension))] += _safe_int(row.get(metric))
        return self._named_values(values, limit=limit)

    def _cube_date_values(
        self,
        rows: list[dict[str, Any]],
        filters: dict[str, str | None],
        metric: str,
        round_values: bool = False,
    ) -> list[dict[str, Any]]:
        values: dict[str, float] = defaultdict(float)
        for row in rows:
            if not self._cube_row_matches_filters(row, filters):
                continue
            date = _normalized_text(row.get("dt"), "")
            if not date or date == DASHBOARD_CUBE_ALL_VALUE:
                continue
            values[date] += _safe_float(row.get(metric))
        return self._date_values(values, round_values=round_values)

    @staticmethod
    def _cube_row_matches_filters(
        row: dict[str, Any],
        filters: dict[str, str | None],
        expansion_dimension: str | None = None,
    ) -> bool:
        for dimension in DASHBOARD_CUBE_DIMENSIONS:
            expected = filters.get(dimension)
            actual = row.get(dimension)
            if expected:
                if actual != expected:
                    return False
                continue
            if dimension == expansion_dimension:
                if actual == DASHBOARD_CUBE_ALL_VALUE:
                    return False
                continue
            if actual != DASHBOARD_CUBE_ALL_VALUE:
                return False
        return True

    def _dashboard_metric_definitions(self) -> list[dict[str, Any]]:
        manifest = self._load_run_manifest()
        run_id = _normalized_text(manifest.get("run_id"), "local-cache") if manifest else "local-cache"
        for path in self._dashboard_semantic_candidates():
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, list):
                return payload
        return dashboard_metric_definitions(run_id)

    def _dashboard_semantic_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        manifest = self._load_run_manifest()
        artifacts = manifest.get("output_artifacts", {}) if isinstance(manifest, dict) else {}
        cube_artifacts = artifacts.get("dashboard_cube_artifacts") or artifacts.get("dashboard_cube") or {}
        if isinstance(cube_artifacts, dict) and cube_artifacts.get("semantic_metrics"):
            candidates.extend(self._resolve_relative_path(str(cube_artifacts["semantic_metrics"])))
        candidates.append(self.cache_dir / "dashboard_semantic_metrics.json")
        return self._dedupe_paths(candidates)

    def _iter_table_rows(self, csv_paths: list[Path], source_dataset: str):
        for path in csv_paths:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    yield _normalized_table_row(row, source_dataset)

    @staticmethod
    def _matches_filters(
        row: dict[str, str],
        event_type: str | None,
        brand: str | None,
        category_level1: str | None,
    ) -> bool:
        if event_type and row.get("event_type") != event_type:
            return False
        if brand and row.get("brand") != brand:
            return False
        if category_level1 and row.get("category_level1") != category_level1:
            return False
        return True

    def _dashboard_slice_evidence(
        self,
        source_dataset: str,
        filtered_row_count: int,
        total_row_count: int,
        query_ms: float,
        filters: dict[str, str | None],
        cache_mode: str,
        cache_hit: bool,
        fallback_reason: str | None = None,
        cube_path: str | None = None,
        cube_paths: dict[str, str] | None = None,
        cube_row_count: int | None = None,
        contract_version: str | None = None,
        semantic_version: str | None = None,
        metric_grain: str | None = None,
        metric_definitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        manifest = self._load_run_manifest()
        run_id = _normalized_text(manifest.get("run_id"), "local-cache") if manifest else "local-cache"
        resolved_contract_version = contract_version or (
            _normalized_text(manifest.get("contract_version"), "dashboard-slice/v1") if manifest else "dashboard-slice/v1"
        )
        coverage_rate = filtered_row_count / total_row_count if total_row_count else 0
        generated_at = (
            manifest.get("generated_at")
            or manifest.get("completed_at")
            or datetime.now(timezone.utc).isoformat()
            if manifest
            else datetime.now(timezone.utc).isoformat()
        )
        return {
            "source_dataset": source_dataset,
            "filtered_row_count": filtered_row_count,
            "total_row_count": total_row_count,
            "coverage_rate": round(coverage_rate, 6),
            "query_ms": round(query_ms, 2),
            "run_id": run_id,
            "contract_version": resolved_contract_version,
            "dataset_version": f"{run_id}:{resolved_contract_version}",
            "generated_at": generated_at,
            "refreshed_at": generated_at,
            "spark_duration": manifest.get("elapsed_seconds") if manifest else None,
            "filters": {key: value for key, value in filters.items() if value},
            "cache_mode": cache_mode,
            "cache_hit": cache_hit,
            "fallback_reason": fallback_reason,
            "cube_path": cube_path,
            "cube_paths": cube_paths,
            "cube_row_count": cube_row_count,
            "semantic_version": semantic_version,
            "metric_grain": metric_grain,
            "metric_definitions": metric_definitions or [],
        }

    def _load_run_manifest(self) -> dict[str, Any]:
        manifest_path = self.cache_dir / "run_manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _named_values(values: dict[str, int], limit: int | None = None) -> list[dict[str, Any]]:
        rows = [{"name": name, "value": value} for name, value in values.items()]
        rows.sort(key=lambda item: (-item["value"], item["name"]))
        return rows[:limit] if limit else rows

    @staticmethod
    def _date_values(values: dict[str, float] | dict[str, int], round_values: bool = False) -> list[dict[str, Any]]:
        rows = []
        for date, value in sorted(values.items()):
            rows.append({"date": date, "value": round(value, 2) if round_values else value})
        return rows

    def _cleaned_table_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        if self.cleaned_table_path:
            candidates.append(self.cleaned_table_path)

        manifest_path = self.cache_dir / "run_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                table_events = manifest.get("output_artifacts", {}).get("table_events")
                if table_events:
                    candidates.extend(self._resolve_relative_path(table_events))
            except (OSError, json.JSONDecodeError):
                pass

        candidates.extend([self.cache_dir / "table_events", self.cache_dir / "table_events.csv"])
        deduped: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key not in seen:
                deduped.append(path)
                seen.add(key)
        return deduped

    @staticmethod
    def _dedupe_paths(candidates: list[Path]) -> list[Path]:
        deduped: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key not in seen:
                deduped.append(path)
                seen.add(key)
        return deduped

    def _resolve_relative_path(self, value: str) -> list[Path]:
        path = Path(value)
        if path.is_absolute():
            return [path]
        return [path, self.cache_dir.parent.parent / path, self.cache_dir / path.name]

    @staticmethod
    def _csv_paths(path: Path) -> list[Path]:
        if path.is_file() and path.suffix == ".csv":
            return [path]
        if not path.is_dir():
            return []
        return sorted(item for item in path.rglob("*.csv") if item.is_file() and not item.name.startswith("."))
