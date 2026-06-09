from __future__ import annotations

from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.schemas import EVENT_TYPES


def clean_events(df: DataFrame) -> DataFrame:
    """Normalize and clean ecommerce event rows."""
    normalized = (
        df.withColumn("event_timestamp", F.to_timestamp("event_time", "yyyy-MM-dd HH:mm:ss z"))
        .withColumn(
            "event_timestamp",
            F.coalesce("event_timestamp", F.to_timestamp("event_time", "yyyy-MM-dd HH:mm:ss")),
        )
        .withColumn("event_date", F.to_date("event_timestamp"))
        .withColumn("event_hour", F.hour("event_timestamp"))
        .withColumn("brand", F.coalesce(F.nullif(F.trim("brand"), F.lit("")), F.lit("unknown")))
        .withColumn("category_code", F.coalesce(F.nullif(F.trim("category_code"), F.lit("")), F.lit("unknown")))
        .withColumn("user_session", F.coalesce(F.nullif(F.trim("user_session"), F.lit("")), F.lit("unknown")))
        .withColumn("category_level1", F.split("category_code", r"\.").getItem(0))
        .withColumn("category_level2", F.split("category_code", r"\.").getItem(1))
    )

    cleaned = (
        normalized.filter(F.col("event_type").isin(EVENT_TYPES))
        .filter(F.col("event_timestamp").isNotNull())
        .filter(F.col("product_id").isNotNull())
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("price").isNull() | ((F.col("price") >= 0) & (F.col("price") <= 100000)))
        .dropDuplicates(["event_time", "event_type", "product_id", "user_id", "user_session"])
    )
    return cleaned


def build_quality_report(raw_df: DataFrame, cleaned_df: DataFrame) -> dict[str, Any]:
    raw_count = raw_df.count()
    cleaned_count = cleaned_df.count()
    duplicate_count = raw_count - raw_df.dropDuplicates(
        ["event_time", "event_type", "product_id", "user_id", "user_session"]
    ).count()
    invalid_price_count = raw_df.filter((F.col("price") < 0) | (F.col("price") > 100000)).count()
    missing_brand_count = raw_df.filter(F.col("brand").isNull() | (F.trim("brand") == "")).count()

    removed_count = raw_count - cleaned_count
    valid_event_type_count = raw_df.filter(F.col("event_type").isin(EVENT_TYPES)).count()
    missing_required_key_count = raw_df.filter(
        F.col("event_time").isNull()
        | F.col("event_type").isNull()
        | F.col("product_id").isNull()
        | F.col("user_id").isNull()
        | F.col("user_session").isNull()
    ).count()

    return {
        "raw_rows": raw_count,
        "cleaned_rows": cleaned_count,
        "removed_rows": removed_count,
        "removed_ratio": round(removed_count / raw_count, 6) if raw_count else 0,
        "duplicate_rows": duplicate_count,
        "invalid_price_rows": invalid_price_count,
        "missing_brand_rows": missing_brand_count,
        "valid_event_type_rows": valid_event_type_count,
        "missing_required_key_rows": missing_required_key_count,
    }


def evaluate_quality(report: dict[str, Any], thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    thresholds = thresholds or {}
    checks = []

    def add_check(name: str, actual: float, operator: str, expected: float) -> None:
        passed = actual <= expected if operator == "<=" else actual >= expected
        checks.append(
            {
                "name": name,
                "actual": actual,
                "operator": operator,
                "expected": expected,
                "passed": passed,
            }
        )

    if "max_removed_ratio" in thresholds:
        add_check("removed_ratio", float(report.get("removed_ratio", 0)), "<=", float(thresholds["max_removed_ratio"]))
    if "max_invalid_price_rows" in thresholds:
        add_check(
            "invalid_price_rows",
            float(report.get("invalid_price_rows", 0)),
            "<=",
            float(thresholds["max_invalid_price_rows"]),
        )
    if "min_cleaned_rows" in thresholds:
        add_check("cleaned_rows", float(report.get("cleaned_rows", 0)), ">=", float(thresholds["min_cleaned_rows"]))
    if "max_ordering_anomaly_ratio" in thresholds:
        add_check(
            "ordering_anomaly_ratio",
            float(report.get("ordering_anomaly_ratio", 0)),
            "<=",
            float(thresholds["max_ordering_anomaly_ratio"]),
        )
    if "max_purchase_missing_price_ratio" in thresholds:
        add_check(
            "purchase_missing_price_ratio",
            float(report.get("purchase_missing_price_ratio", 0)),
            "<=",
            float(thresholds["max_purchase_missing_price_ratio"]),
        )
    if "min_session_fact_rows" in thresholds:
        add_check(
            "session_fact_rows",
            float(report.get("session_fact_rows", 0)),
            ">=",
            float(thresholds["min_session_fact_rows"]),
        )

    status = "passed" if all(check["passed"] for check in checks) else "failed"
    if not checks:
        status = "not_evaluated"
    return {"status": status, "checks": checks, "thresholds": thresholds}
