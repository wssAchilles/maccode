from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


FEATURE_MART_CONTRACT_VERSION = "behavior-feature-mart/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "max_freshness_lag_hours": 5_300_000 / 60,
    "late_arrival_days": 7,
    "max_duplicate_event_key_rate": 0.01,
    "max_quarantined_rate": 0.05,
}


def feature_mart_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_feature_mart_outputs(
    raw_df: DataFrame,
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    events = add_event_keys(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    deduped_events = events.dropDuplicates(["event_key"]).persist(StorageLevel.MEMORY_AND_DISK)
    daily_product = build_daily_product_behavior(deduped_events, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    daily_user = build_daily_user_behavior(deduped_events, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    daily_category = build_daily_category_behavior(deduped_events, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    quality = build_event_quality_audit(raw_df, cleaned_df, events, deduped_events, run_id, config)
    freshness = build_freshness_report(deduped_events, run_id, config)
    partitions = build_partition_report(deduped_events, run_id)
    summary = build_feature_mart_summary(run_id, input_snapshot, quality, freshness, partitions)
    previews = build_feature_mart_previews(daily_product, daily_category, daily_user, int(config["preview_limit"]))

    frames = {
        "daily_product_behavior": daily_product,
        "daily_user_behavior": daily_user,
        "daily_category_behavior": daily_category,
        "event_quality_audit": raw_df.sparkSession.createDataFrame([_event_quality_row(quality)]),
        "late_arrival_audit": raw_df.sparkSession.createDataFrame([_late_arrival_row(freshness)]),
    }
    metrics = {
        "feature_mart_summary": summary,
        "feature_mart_freshness": freshness,
        "feature_mart_quality": quality,
        "feature_mart_partitions": partitions,
        "feature_mart_products": previews["products"],
        "feature_mart_categories": previews["categories"],
        "feature_mart_users": previews["users"],
    }
    events.unpersist()
    deduped_events.unpersist()
    return frames, metrics


def add_event_keys(cleaned_df: DataFrame) -> DataFrame:
    event_key = F.sha2(
        F.concat_ws(
            "||",
            F.coalesce(F.col("event_time").cast("string"), F.lit("")),
            F.coalesce(F.col("event_type").cast("string"), F.lit("")),
            F.coalesce(F.col("product_id").cast("string"), F.lit("")),
            F.coalesce(F.col("user_id").cast("string"), F.lit("")),
            F.coalesce(F.col("user_session").cast("string"), F.lit("")),
            F.coalesce(F.col("price").cast("string"), F.lit("")),
        ),
        256,
    )
    return cleaned_df.withColumn("event_key", event_key).withColumn("dt", F.col("event_date").cast("string"))


def build_daily_product_behavior(events: DataFrame, run_id: str) -> DataFrame:
    return (
        events.groupBy("dt", "product_id", "brand", "category_level1")
        .agg(
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.countDistinct("user_id").alias("unique_users"),
            F.countDistinct("user_session").alias("unique_sessions"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias(
                "revenue"
            ),
            F.round(F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))), 2).alias("avg_price"),
            F.min("event_timestamp").alias("first_event_time"),
            F.max("event_timestamp").alias("last_event_time"),
        )
        .withColumn("view_to_cart_rate", _safe_divide(F.col("carts"), F.col("views")))
        .withColumn("cart_to_purchase_rate", _safe_divide(F.col("purchases"), F.col("carts")))
        .withColumn("view_to_purchase_rate", _safe_divide(F.col("purchases"), F.col("views")))
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(FEATURE_MART_CONTRACT_VERSION))
    )


def build_daily_user_behavior(events: DataFrame, run_id: str) -> DataFrame:
    preference_counts = events.groupBy("dt", "user_id", "category_level1").agg(F.count("*").alias("category_events"))
    preference_window = Window.partitionBy("dt", "user_id").orderBy(F.desc("category_events"), F.asc("category_level1"))
    preferences = (
        preference_counts.withColumn("preference_rank", F.row_number().over(preference_window))
        .filter(F.col("preference_rank") == 1)
        .select("dt", "user_id", F.col("category_level1").alias("preferred_category_level1"))
    )
    base = (
        events.groupBy("dt", "user_id")
        .agg(
            F.countDistinct("user_session").alias("sessions"),
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias(
                "revenue"
            ),
            F.round((F.max(F.unix_timestamp("event_timestamp")) - F.min(F.unix_timestamp("event_timestamp"))) / 60, 2).alias(
                "active_minutes"
            ),
            F.countDistinct("product_id").alias("distinct_products"),
            F.countDistinct("category_level1").alias("distinct_categories"),
            F.max("event_timestamp").alias("last_event_time"),
        )
        .join(preferences, on=["dt", "user_id"], how="left")
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(FEATURE_MART_CONTRACT_VERSION))
    )
    return base


def build_daily_category_behavior(events: DataFrame, run_id: str) -> DataFrame:
    return (
        events.groupBy("dt", "category_level1")
        .agg(
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.countDistinct("user_id").alias("unique_users"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias(
                "revenue"
            ),
            F.round(F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))), 2).alias("avg_price"),
        )
        .withColumn("conversion_rate", _safe_divide(F.col("purchases"), F.col("views")))
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(FEATURE_MART_CONTRACT_VERSION))
    )


def build_event_quality_audit(
    raw_df: DataFrame,
    cleaned_df: DataFrame,
    events: DataFrame,
    deduped_events: DataFrame,
    run_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    raw_rows = raw_df.count()
    cleaned_rows = cleaned_df.count()
    event_rows = events.count()
    deduped_rows = deduped_events.count()
    duplicate_event_keys = event_rows - deduped_rows
    invalid_event_type_rows = raw_df.filter(~F.col("event_type").isin("view", "cart", "purchase")).count()
    missing_user_rows = raw_df.filter(F.col("user_id").isNull()).count()
    missing_product_rows = raw_df.filter(F.col("product_id").isNull()).count()
    purchase_missing_or_invalid_price_rows = raw_df.filter(
        (F.col("event_type") == "purchase") & (F.col("price").isNull() | (F.col("price") <= 0))
    ).count()
    null_session_rows = raw_df.filter(F.col("user_session").isNull() | (F.trim("user_session") == "")).count()
    quarantined_rows = raw_rows - cleaned_rows + duplicate_event_keys
    duplicate_event_key_rate = _safe_rate(duplicate_event_keys, max(event_rows, 1))
    quarantined_rate = _safe_rate(quarantined_rows, max(raw_rows, 1))
    checks = [
        _check("duplicate_event_key_rate", duplicate_event_key_rate, "<=", float(config["max_duplicate_event_key_rate"])),
        _check("quarantined_rate", quarantined_rate, "<=", float(config["max_quarantined_rate"])),
    ]
    quality_status = "passed" if all(check["passed"] for check in checks) else "failed"
    return {
        "run_id": run_id,
        "contract_version": FEATURE_MART_CONTRACT_VERSION,
        "raw_rows": raw_rows,
        "cleaned_rows": cleaned_rows,
        "deduped_event_rows": deduped_rows,
        "duplicate_event_keys": duplicate_event_keys,
        "duplicate_event_key_rate": duplicate_event_key_rate,
        "invalid_event_type_rows": invalid_event_type_rows,
        "missing_user_rows": missing_user_rows,
        "missing_product_rows": missing_product_rows,
        "purchase_missing_or_invalid_price_rows": purchase_missing_or_invalid_price_rows,
        "null_session_rows": null_session_rows,
        "quarantined_rows": quarantined_rows,
        "quarantined_rate": quarantined_rate,
        "checks": checks,
        "quality_status": quality_status,
    }


def build_freshness_report(events: DataFrame, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
    row = events.agg(F.min("event_timestamp").alias("min_event_time"), F.max("event_timestamp").alias("max_event_time")).first()
    max_event_time = row["max_event_time"]
    min_event_time = row["min_event_time"]
    generated_at = datetime.now(UTC)
    late_cutoff = max_event_time - timedelta(days=int(config["late_arrival_days"])) if max_event_time else None
    late_rows = events.filter(F.col("event_timestamp") < F.lit(late_cutoff)).count() if late_cutoff else 0
    total_rows = events.count()
    freshness_lag_hours = (
        round((generated_at - max_event_time.replace(tzinfo=UTC)).total_seconds() / 3600, 4) if max_event_time else None
    )
    late_rate = _safe_rate(late_rows, max(total_rows, 1))
    max_lag = float(config["max_freshness_lag_hours"])
    sla_status = "passed" if freshness_lag_hours is not None and freshness_lag_hours <= max_lag else "stale"
    affected_dates = [
        row["dt"]
        for row in events.filter(F.col("event_timestamp") < F.lit(late_cutoff)).select("dt").distinct().orderBy("dt").collect()
    ] if late_cutoff else []
    return {
        "run_id": run_id,
        "contract_version": FEATURE_MART_CONTRACT_VERSION,
        "generated_at": generated_at.isoformat(),
        "min_event_time": min_event_time.isoformat() if min_event_time else None,
        "max_event_time": max_event_time.isoformat() if max_event_time else None,
        "watermark_time": late_cutoff.isoformat() if late_cutoff else None,
        "late_rows": late_rows,
        "late_rate": late_rate,
        "affected_dates": affected_dates,
        "freshness_lag_hours": freshness_lag_hours,
        "max_freshness_lag_hours": max_lag,
        "sla_status": sla_status,
    }


def build_partition_report(events: DataFrame, run_id: str) -> dict[str, Any]:
    rows = events.groupBy("dt").agg(F.count("*").alias("rows")).orderBy("dt").collect()
    partitions = [{"dt": row["dt"], "rows": int(row["rows"]), "status": "written"} for row in rows if row["dt"]]
    dates = [row["dt"] for row in partitions]
    return {
        "run_id": run_id,
        "contract_version": FEATURE_MART_CONTRACT_VERSION,
        "expected": len(dates),
        "written": len(dates),
        "missing": [],
        "min_dt": min(dates) if dates else None,
        "max_dt": max(dates) if dates else None,
        "partitions": partitions,
    }


def build_feature_mart_summary(
    run_id: str,
    input_snapshot: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
    partitions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": FEATURE_MART_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "date_range": {"min_dt": partitions["min_dt"], "max_dt": partitions["max_dt"]},
        "partitions": {"expected": partitions["expected"], "written": partitions["written"], "missing": partitions["missing"]},
        "freshness": {
            "max_event_time": freshness["max_event_time"],
            "freshness_lag_hours": freshness["freshness_lag_hours"],
            "sla_status": freshness["sla_status"],
        },
        "quality_status": quality["quality_status"],
        "raw_rows": quality["raw_rows"],
        "cleaned_rows": quality["cleaned_rows"],
        "deduped_event_rows": quality["deduped_event_rows"],
    }


def build_feature_mart_previews(
    daily_product: DataFrame,
    daily_category: DataFrame,
    daily_user: DataFrame,
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    products = [
        _json_safe(row.asDict())
        for row in daily_product.orderBy(F.desc("dt"), F.desc("revenue"), F.desc("views")).limit(limit).collect()
    ]
    categories = [
        _json_safe(row.asDict())
        for row in daily_category.orderBy(F.desc("dt"), F.desc("revenue"), F.desc("views")).limit(limit).collect()
    ]
    users = [
        _json_safe(row.asDict())
        for row in daily_user.orderBy(F.desc("dt"), F.desc("revenue"), F.desc("views")).limit(limit).collect()
    ]
    return {"products": products, "categories": categories, "users": users}


def _safe_divide(numerator: F.Column, denominator: F.Column) -> F.Column:
    return F.round(numerator / F.when(denominator == 0, None).otherwise(denominator), 6)


def _safe_rate(numerator: float | int, denominator: float | int) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _check(name: str, actual: float, operator: str, expected: float) -> dict[str, Any]:
    passed = actual <= expected if operator == "<=" else actual >= expected
    return {"name": name, "actual": actual, "operator": operator, "expected": expected, "passed": passed}


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    safe = {}
    for key, value in row.items():
        safe[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return safe


def _late_arrival_row(freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": freshness["run_id"],
        "contract_version": freshness["contract_version"],
        "max_event_time": freshness["max_event_time"],
        "min_event_time": freshness["min_event_time"],
        "watermark_time": freshness["watermark_time"],
        "late_rows": freshness["late_rows"],
        "late_rate": freshness["late_rate"],
        "affected_dates": ",".join(freshness["affected_dates"]),
        "freshness_lag_hours": freshness["freshness_lag_hours"],
        "sla_status": freshness["sla_status"],
    }


def _event_quality_row(quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": quality["run_id"],
        "contract_version": quality["contract_version"],
        "raw_rows": quality["raw_rows"],
        "cleaned_rows": quality["cleaned_rows"],
        "deduped_event_rows": quality["deduped_event_rows"],
        "duplicate_event_keys": quality["duplicate_event_keys"],
        "duplicate_event_key_rate": quality["duplicate_event_key_rate"],
        "invalid_event_type_rows": quality["invalid_event_type_rows"],
        "missing_user_rows": quality["missing_user_rows"],
        "missing_product_rows": quality["missing_product_rows"],
        "purchase_missing_or_invalid_price_rows": quality["purchase_missing_or_invalid_price_rows"],
        "null_session_rows": quality["null_session_rows"],
        "quarantined_rows": quality["quarantined_rows"],
        "quarantined_rate": quality["quarantined_rate"],
        "quality_status": quality["quality_status"],
    }
