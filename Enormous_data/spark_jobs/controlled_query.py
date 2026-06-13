from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

CONTRACT_VERSION = "controlled-natural-query/v1"
MAX_LIMIT = 50
DEFAULT_LIMIT = 12
DEFAULT_SUGGESTIONS = [
    "按月份统计销售额",
    "按日期统计事件量",
    "按类目统计购买数",
    "按品牌统计销售额",
    "按行为类型统计事件量",
]

METRIC_LABELS = {
    "event_count": "事件量",
    "purchase_count": "购买数",
    "total_sales": "成交额",
}

DIMENSION_LABELS = {
    "date": "日期",
    "month": "月份",
    "category_level1": "一级类目",
    "brand": "品牌",
    "event_type": "行为类型",
}

EVENT_TYPE_LABELS = {
    "view": "浏览",
    "cart": "加购",
    "remove_from_cart": "移出购物车",
    "purchase": "购买",
}


@dataclass(frozen=True)
class ControlledQueryIntent:
    metric: str
    metric_label: str
    dimension: str
    dimension_label: str
    aggregation: str
    chart_type: str
    limit: int
    time_grain: str | None = None
    event_type_filter: str | None = None
    event_type_filter_label: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "ControlledQueryIntent":
        return cls(
            metric=str(payload["metric"]),
            metric_label=str(payload.get("metric_label") or METRIC_LABELS.get(str(payload["metric"]), payload["metric"])),
            dimension=str(payload["dimension"]),
            dimension_label=str(payload.get("dimension_label") or DIMENSION_LABELS.get(str(payload["dimension"]), payload["dimension"])),
            aggregation=str(payload.get("aggregation") or "count"),
            chart_type=str(payload.get("chart_type") or "bar"),
            limit=int(payload.get("limit") or DEFAULT_LIMIT),
            time_grain=payload.get("time_grain"),
            event_type_filter=payload.get("event_type_filter"),
            event_type_filter_label=payload.get("event_type_filter_label"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledQueryParseResult:
    matched: bool
    intent: ControlledQueryIntent | None
    confidence: float
    reason: str | None = None
    suggestions: tuple[str, ...] = tuple(DEFAULT_SUGGESTIONS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "intent": self.intent.to_dict() if self.intent else None,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggestions": list(self.suggestions),
        }


def parse_controlled_query(query: str) -> ControlledQueryParseResult:
    text = _normalized_query(query)
    if not text:
        return _unmatched("请输入一个中文分析问题")

    dimension = _infer_dimension(text)
    metric, metric_label, event_type_filter = _infer_metric(text)
    if not dimension:
        return _unmatched("暂未识别分析维度，可尝试按月份、日期、类目、品牌或行为类型提问")
    if not metric:
        return _unmatched("暂未识别指标，可尝试统计销售额、购买数或事件量")

    aggregation = "sum" if metric == "total_sales" else "count"
    intent = ControlledQueryIntent(
        metric=metric,
        metric_label=metric_label,
        dimension=dimension,
        dimension_label=DIMENSION_LABELS[dimension],
        aggregation=aggregation,
        chart_type="line" if dimension in {"date", "month"} else "horizontal_bar",
        limit=_infer_limit(text),
        time_grain=dimension if dimension in {"date", "month"} else None,
        event_type_filter=event_type_filter,
        event_type_filter_label=EVENT_TYPE_LABELS.get(event_type_filter) if event_type_filter else None,
    )
    return ControlledQueryParseResult(matched=True, intent=intent, confidence=0.92)


def execute_controlled_query_dataframe(df: Any, intent_payload: ControlledQueryIntent | dict[str, Any]) -> list[dict[str, Any]]:
    """Execute a parsed intent on a Spark DataFrame with code-defined columns only."""
    from pyspark.sql import functions as F

    intent = intent_payload if isinstance(intent_payload, ControlledQueryIntent) else ControlledQueryIntent.from_mapping(intent_payload)
    working = df
    if intent.metric in {"purchase_count", "total_sales"}:
        working = working.filter(F.col("event_type") == "purchase")
    elif intent.event_type_filter:
        working = working.filter(F.col("event_type") == intent.event_type_filter)

    dimension_column = _spark_dimension_column(F, working, intent.dimension)
    metric_column = (
        F.round(F.sum(F.col("price").cast("double")), 2)
        if intent.metric == "total_sales"
        else F.count(F.lit(1)).cast("double")
    )
    grouped = working.withColumn("__dimension", dimension_column).groupBy("__dimension").agg(metric_column.alias("__value"))
    if intent.dimension in {"date", "month"}:
        ordered = grouped.orderBy("__dimension")
    else:
        ordered = grouped.orderBy(F.desc("__value"), "__dimension")

    rows = ordered.limit(intent.limit).collect()
    return [
        {"name": str(row["__dimension"] or "unknown"), "value": float(row["__value"] or 0)}
        for row in rows
        if row["__dimension"] is not None
    ]


def _spark_dimension_column(F: Any, df: Any, dimension: str) -> Any:
    if dimension == "month":
        return F.date_format(_spark_event_date(F, df), "yyyy-MM")
    if dimension == "date":
        return F.date_format(_spark_event_date(F, df), "yyyy-MM-dd")
    if dimension in {"category_level1", "brand", "event_type"}:
        return F.col(dimension)
    raise ValueError(f"unsupported controlled query dimension: {dimension}")


def _spark_event_date(F: Any, df: Any) -> Any:
    if "event_timestamp" in df.columns:
        return F.to_timestamp(F.col("event_timestamp"))
    if "event_time" in df.columns:
        return F.to_timestamp(F.col("event_time"))
    if "event_date" in df.columns:
        return F.to_timestamp(F.col("event_date").cast("string"))
    raise ValueError("controlled query requires event_timestamp, event_time, or event_date")


def _unmatched(reason: str) -> ControlledQueryParseResult:
    return ControlledQueryParseResult(matched=False, intent=None, confidence=0, reason=reason)


def _normalized_query(query: str) -> str:
    return re.sub(r"\s+", "", str(query or "").strip().lower())


def _infer_dimension(text: str) -> str | None:
    if any(token in text for token in ("月份", "按月", "每月", "月度")):
        return "month"
    if any(token in text for token in ("日期", "按日", "每天", "每日", "天统计")):
        return "date"
    if any(token in text for token in ("类目", "品类", "一级类目", "category")):
        return "category_level1"
    if any(token in text for token in ("品牌", "brand")):
        return "brand"
    if any(token in text for token in ("行为类型", "事件类型", "行为分布", "事件分布")):
        return "event_type"
    return None


def _infer_metric(text: str) -> tuple[str | None, str, str | None]:
    if any(token in text for token in ("销售额", "成交额", "营收", "gmv")):
        return "total_sales", METRIC_LABELS["total_sales"], None
    if any(token in text for token in ("购买数", "购买量", "订单数", "下单数")):
        return "purchase_count", METRIC_LABELS["purchase_count"], None
    if any(token in text for token in ("浏览数", "浏览量")):
        return "event_count", "浏览数", "view"
    if any(token in text for token in ("加购数", "加购量")):
        return "event_count", "加购数", "cart"
    if any(token in text for token in ("事件量", "事件数", "行为量", "行为数")):
        return "event_count", METRIC_LABELS["event_count"], None
    return None, "", None


def _infer_limit(text: str) -> int:
    match = re.search(r"(?:top|前|最多)(\d{1,3})", text)
    if not match:
        return DEFAULT_LIMIT
    return max(1, min(MAX_LIMIT, int(match.group(1))))
