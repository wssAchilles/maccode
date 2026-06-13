from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from app.services.metric_cache import MetricCache
from spark_jobs.controlled_query import CONTRACT_VERSION
from spark_jobs.controlled_query import DEFAULT_SUGGESTIONS
from spark_jobs.controlled_query import ControlledQueryIntent
from spark_jobs.controlled_query import parse_controlled_query


class UnsupportedControlledQuery(ValueError):
    pass


def run_controlled_query(metric_cache: MetricCache, query: str) -> dict[str, Any]:
    started = time.perf_counter()
    parse_result = parse_controlled_query(query)
    if not parse_result.matched or parse_result.intent is None:
        return _unsupported_payload(query, parse_result.reason or "暂不支持该问法", time.perf_counter() - started)

    intent = parse_result.intent
    try:
        rows, evidence, execution_engine = _execute_from_cache(metric_cache, intent)
    except UnsupportedControlledQuery as error:
        return _unsupported_payload(query, str(error), time.perf_counter() - started, intent=intent)

    rows = _with_share(_sort_rows(rows, intent))
    evidence = {
        **evidence,
        "query_ms": round((time.perf_counter() - started) * 1000, 2),
        "row_count": len(rows),
        "execution_engine": execution_engine,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "query": query,
        "status": "matched",
        "matched": True,
        "message": "已识别为受控查询，结果来自物化指标或缓存数据。",
        "confidence": parse_result.confidence,
        "intent": intent.to_dict(),
        "chart": _chart_spec(intent),
        "rows": rows,
        "suggestions": list(DEFAULT_SUGGESTIONS),
        "insight": _insight(intent, rows),
        "evidence": evidence,
    }


def _execute_from_cache(metric_cache: MetricCache, intent: ControlledQueryIntent) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    if intent.dimension == "brand":
        return _brand_rows(metric_cache, intent)

    event_filter = intent.event_type_filter
    if intent.metric == "purchase_count":
        event_filter = "purchase"
    slice_payload = metric_cache.load_dashboard_slice(event_type=event_filter)
    evidence = _evidence_from_slice(slice_payload)

    if intent.dimension in {"date", "month"}:
        if intent.metric == "total_sales":
            rows = _date_rows(slice_payload.get("daily_sales", []), intent)
        elif intent.metric in {"event_count", "purchase_count"}:
            rows = _date_rows(slice_payload.get("daily_events", []), intent)
        else:
            raise UnsupportedControlledQuery("当前指标暂不支持按时间统计")
        return rows, evidence, "dashboard_slice_cache"

    if intent.dimension == "category_level1":
        if intent.metric not in {"event_count", "purchase_count"}:
            raise UnsupportedControlledQuery("当前缓存暂不支持按类目统计成交额，可先尝试按类目统计购买数")
        return _named_rows(slice_payload.get("top_categories", []), intent), evidence, "dashboard_slice_cache"

    if intent.dimension == "event_type":
        if intent.metric != "event_count":
            raise UnsupportedControlledQuery("行为类型维度当前只支持统计事件量")
        return _named_rows(slice_payload.get("event_type_count", []), intent), evidence, "dashboard_slice_cache"

    raise UnsupportedControlledQuery("暂不支持该指标与维度组合")


def _brand_rows(metric_cache: MetricCache, intent: ControlledQueryIntent) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    if intent.metric not in {"total_sales", "purchase_count"}:
        raise UnsupportedControlledQuery("品牌维度当前支持统计成交额或购买数")
    rows = []
    for row in metric_cache.load_metric("top_brands")[: intent.limit]:
        value = row.get("value") if intent.metric == "total_sales" else row.get("orders", row.get("value"))
        rows.append({"name": _text(row.get("name")), "raw_name": row.get("name"), "value": _number(value)})
    evidence = _evidence_from_slice(metric_cache.load_dashboard_slice())
    return rows, evidence, "top_brand_metric_cache"


def _date_rows(rows: list[dict[str, Any]], intent: ControlledQueryIntent) -> list[dict[str, Any]]:
    if intent.dimension == "date":
        return [{"name": _text(row.get("date")), "raw_name": row.get("date"), "value": _number(row.get("value"))} for row in rows]

    monthly: dict[str, float] = defaultdict(float)
    for row in rows:
        date = _text(row.get("date"), "")
        if len(date) < 7:
            continue
        monthly[date[:7]] += _number(row.get("value"))
    return [{"name": month, "raw_name": month, "value": round(value, 2)} for month, value in sorted(monthly.items())]


def _named_rows(rows: list[dict[str, Any]], intent: ControlledQueryIntent) -> list[dict[str, Any]]:
    return [
        {
            "name": _text(row.get("name")),
            "raw_name": row.get("name"),
            "value": _number(row.get("value")),
        }
        for row in rows[: intent.limit]
    ]


def _sort_rows(rows: list[dict[str, Any]], intent: ControlledQueryIntent) -> list[dict[str, Any]]:
    if intent.dimension in {"date", "month"}:
        return rows[: intent.limit]
    return sorted(rows, key=lambda row: (-_number(row.get("value")), _text(row.get("name"))))[: intent.limit]


def _with_share(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(_number(row.get("value")) for row in rows)
    if total <= 0:
        return [{**row, "share": 0} for row in rows]
    return [{**row, "share": round(_number(row.get("value")) / total, 6)} for row in rows]


def _chart_spec(intent: ControlledQueryIntent) -> dict[str, Any]:
    return {
        "type": intent.chart_type,
        "title": f"按{intent.dimension_label}统计{intent.metric_label}",
        "x_field": "name",
        "y_field": "value",
        "series_name": intent.metric_label,
        "dimension_label": intent.dimension_label,
        "metric_label": intent.metric_label,
    }


def _evidence_from_slice(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("evidence") or {}
    return {
        "source_dataset": evidence.get("source_dataset", "metric_cache"),
        "run_id": evidence.get("run_id", "local-cache"),
        "contract_version": evidence.get("contract_version", "dashboard-slice/v1"),
        "dataset_version": evidence.get("dataset_version", "local-cache:dashboard-slice/v1"),
        "generated_at": evidence.get("generated_at"),
        "cache_mode": evidence.get("cache_mode"),
        "cache_hit": evidence.get("cache_hit"),
        "semantic_version": evidence.get("semantic_version"),
        "metric_grain": evidence.get("metric_grain"),
    }


def _insight(intent: ControlledQueryIntent, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "当前查询没有返回可展示的数据。"
    if intent.dimension in {"date", "month"}:
        top = max(rows, key=lambda row: _number(row.get("value")))
        return f"{top['name']} 的{intent.metric_label}最高，为 {_format_number(top['value'])}。"
    top = rows[0]
    share = _number(top.get("share")) * 100
    return f"{top['name']} 排名第一，贡献 {_format_number(top['value'])}，占比 {share:.1f}%。"


def _unsupported_payload(
    query: str,
    reason: str,
    elapsed_seconds: float,
    intent: ControlledQueryIntent | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "query": query,
        "status": "unsupported",
        "matched": False,
        "message": reason,
        "confidence": 0,
        "intent": intent.to_dict() if intent else None,
        "chart": {
            "type": "empty",
            "title": "暂不支持该问法",
            "x_field": "name",
            "y_field": "value",
            "series_name": "结果",
            "dimension_label": "维度",
            "metric_label": "指标",
        },
        "rows": [],
        "suggestions": list(DEFAULT_SUGGESTIONS),
        "insight": "请从建议问题中选择一个受控查询。",
        "evidence": {
            "source_dataset": "not_executed",
            "run_id": "not_executed",
            "contract_version": CONTRACT_VERSION,
            "dataset_version": f"not_executed:{CONTRACT_VERSION}",
            "generated_at": None,
            "query_ms": round(elapsed_seconds * 1000, 2),
            "row_count": 0,
            "execution_engine": "not_executed",
        },
    }


def _text(value: Any, fallback: str = "unknown") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_number(value: Any) -> str:
    number = _number(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"
