from __future__ import annotations

from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark import StorageLevel


COHORT_CONTRACT_VERSION = "cohort-retention/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 120,
    "cohort_unit": "month",
    "min_cohort_users": 20,
    "min_cohort_observation_days": 7,
    "max_period_index": 3,
    "high_risk_retention_drop": -0.3,
}

RETENTION_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("cohort", T.StringType()),
        T.StructField("period_index", T.IntegerType()),
        T.StructField("cohort_users", T.LongType()),
        T.StructField("active_users", T.LongType()),
        T.StructField("purchase_users", T.LongType()),
        T.StructField("retention_rate", T.DoubleType()),
        T.StructField("repurchase_rate", T.DoubleType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("quality_status", T.StringType()),
    ]
)

INTERVAL_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("bucket", T.StringType()),
        T.StructField("users", T.LongType()),
        T.StructField("share", T.DoubleType()),
        T.StructField("avg_revenue", T.DoubleType()),
    ]
)

VALUE_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("cohort", T.StringType()),
        T.StructField("period_index", T.IntegerType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("cumulative_revenue", T.DoubleType()),
        T.StructField("revenue_per_purchase_user", T.DoubleType()),
        T.StructField("purchase_users", T.LongType()),
    ]
)

SEGMENT_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("segment_id", T.StringType()),
        T.StructField("cohort", T.StringType()),
        T.StructField("category_level1", T.StringType()),
        T.StructField("users", T.LongType()),
        T.StructField("repeat_purchase_users", T.LongType()),
        T.StructField("repeat_purchase_rate", T.DoubleType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("risk_level", T.StringType()),
        T.StructField("reason_codes", T.ArrayType(T.StringType())),
        T.StructField("recommended_action", T.StringType()),
    ]
)


def cohort_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_cohort_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    preview_limit = int(config["preview_limit"])
    purchases = build_purchase_events(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    user_first = build_user_first_events(purchases).persist(StorageLevel.MEMORY_AND_DISK)
    user_cycles = build_user_purchase_cycles(purchases, user_first).persist(StorageLevel.MEMORY_AND_DISK)
    retention = build_retention_matrix(user_cycles, user_first, config).persist(StorageLevel.MEMORY_AND_DISK)
    value_curves = build_value_curves(retention).persist(StorageLevel.MEMORY_AND_DISK)
    intervals = build_repurchase_intervals(user_cycles).persist(StorageLevel.MEMORY_AND_DISK)
    segments = build_cohort_segments(user_cycles, config).persist(StorageLevel.MEMORY_AND_DISK)

    retention_rows = collect_preview(retention, preview_limit)
    interval_rows = collect_preview(intervals, preview_limit)
    value_preview = collect_preview(value_curves, preview_limit)
    segment_preview = collect_preview(segments, preview_limit)
    quality = build_quality(user_first, retention, intervals, config)
    high_risk_count = int(segments.filter(F.col("risk_level") == "high").count())
    summary = build_summary(user_first, user_cycles, intervals, high_risk_count, quality, config, run_id, input_snapshot)

    frames = {
        "user_first_events": user_first,
        "user_purchase_cycles": user_cycles,
        "cohort_matrix": retention,
        "cohort_value_curves": value_curves,
        "cohort_segments": segments,
    }
    metrics = {
        "cohort_summary": summary,
        "cohort_retention_matrix": retention_rows[:preview_limit],
        "cohort_repurchase_intervals": interval_rows[:preview_limit],
        "cohort_value_curves": value_preview,
        "cohort_segments": segment_preview,
        "cohort_quality": quality,
    }
    purchases.unpersist()
    return frames, metrics


def build_purchase_events(cleaned_df: DataFrame) -> DataFrame:
    return (
        cleaned_df.filter(F.col("event_type") == "purchase")
        .select(
            F.col("user_id").cast("string").alias("user_id"),
            F.col("event_timestamp").alias("purchase_ts"),
            F.coalesce(F.col("category_level1"), F.lit("unknown")).alias("category_level1"),
            F.coalesce(F.col("price"), F.lit(0)).cast("double").alias("price"),
        )
        .filter(F.col("purchase_ts").isNotNull() & F.col("user_id").isNotNull())
    )


def build_user_first_events(purchases: DataFrame) -> DataFrame:
    ranked = purchases.withColumn("purchase_rank", F.row_number().over(Window.partitionBy("user_id").orderBy("purchase_ts")))
    return (
        ranked.filter(F.col("purchase_rank") == 1)
        .select(
            "user_id",
            F.date_format(F.to_date("purchase_ts"), "yyyy-MM").alias("cohort"),
            F.to_date("purchase_ts").alias("first_purchase_date"),
            F.col("category_level1").alias("first_category_level1"),
            F.round(F.col("price"), 2).alias("first_purchase_revenue"),
        )
        .withColumn("contract_version", F.lit(COHORT_CONTRACT_VERSION))
        .select(
            "contract_version",
            "user_id",
            "cohort",
            "first_purchase_date",
            "first_category_level1",
            "first_purchase_revenue",
        )
    )


def build_user_purchase_cycles(purchases: DataFrame, user_first: DataFrame) -> DataFrame:
    user_month = (
        purchases.withColumn("purchase_month", F.date_format(F.to_date("purchase_ts"), "yyyy-MM"))
        .groupBy("user_id", "purchase_month")
        .agg(
            F.count("*").alias("purchase_count"),
            F.round(F.sum("price"), 2).alias("revenue"),
            F.first("category_level1", ignorenulls=True).alias("category_level1"),
            F.min(F.to_date("purchase_ts")).alias("first_purchase_in_period"),
        )
    )
    return (
        user_month.join(
            user_first.select("user_id", "cohort", "first_category_level1", "first_purchase_date"),
            "user_id",
            "inner",
        )
        .withColumn(
            "period_index",
            F.months_between(
                F.to_date(F.concat(F.col("purchase_month"), F.lit("-01"))),
                F.to_date(F.concat(F.col("cohort"), F.lit("-01"))),
            ).cast("int"),
        )
        .filter(F.col("period_index") >= 0)
        .withColumn(
            "is_repurchase_period",
            F.when((F.col("period_index") == 0) & (F.col("purchase_count") > 1), F.lit(1)).otherwise(
                F.when(F.col("period_index") > 0, F.lit(1)).otherwise(F.lit(0))
            ),
        )
        .withColumn("contract_version", F.lit(COHORT_CONTRACT_VERSION))
        .select(
            "contract_version",
            "user_id",
            "cohort",
            "purchase_month",
            "period_index",
            "purchase_count",
            "revenue",
            "category_level1",
            "first_category_level1",
            "is_repurchase_period",
        )
    )


def build_retention_matrix(user_cycles: DataFrame, user_first: DataFrame, config: dict[str, Any]) -> DataFrame:
    cohort_sizes = user_first.groupBy("cohort").agg(F.countDistinct("user_id").alias("cohort_users"))
    matrix = (
        user_cycles.filter(F.col("period_index") <= int(config["max_period_index"]))
        .groupBy("cohort", "period_index")
        .agg(
            F.countDistinct("user_id").alias("active_users"),
            F.countDistinct(F.when(F.col("purchase_count") > 0, F.col("user_id"))).alias("purchase_users"),
            F.countDistinct(F.when(F.col("is_repurchase_period") == 1, F.col("user_id"))).alias("repurchase_users"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
        )
        .join(cohort_sizes, "cohort", "left")
        .withColumn("retention_rate", F.round(F.col("active_users") / F.when(F.col("cohort_users") == 0, None).otherwise(F.col("cohort_users")), 6))
        .withColumn("repurchase_rate", F.round(F.col("repurchase_users") / F.when(F.col("cohort_users") == 0, None).otherwise(F.col("cohort_users")), 6))
        .withColumn("quality_status", F.when(F.col("cohort_users") >= int(config["min_cohort_users"]), F.lit("passed")).otherwise(F.lit("needs_review")))
        .withColumn("contract_version", F.lit(COHORT_CONTRACT_VERSION))
        .select(
            "contract_version",
            "cohort",
            "period_index",
            "cohort_users",
            "active_users",
            "purchase_users",
            "retention_rate",
            "repurchase_rate",
            "revenue",
            "quality_status",
        )
        .orderBy("cohort", "period_index")
    )
    return matrix


def build_value_curves(retention: DataFrame) -> DataFrame:
    window = Window.partitionBy("cohort").orderBy("period_index").rowsBetween(Window.unboundedPreceding, Window.currentRow)
    return (
        retention.withColumn("cumulative_revenue", F.round(F.sum("revenue").over(window), 2))
        .withColumn("revenue_per_purchase_user", F.round(F.col("revenue") / F.when(F.col("purchase_users") == 0, None).otherwise(F.col("purchase_users")), 2))
        .select(
            "contract_version",
            "cohort",
            "period_index",
            "revenue",
            "cumulative_revenue",
            "revenue_per_purchase_user",
            "purchase_users",
        )
        .orderBy("cohort", "period_index")
    )


def build_repurchase_intervals(user_cycles: DataFrame) -> DataFrame:
    user_periods = (
        user_cycles.groupBy("user_id", "cohort")
        .agg(
            F.min(F.when(F.col("period_index") == 0, F.col("period_index"))).alias("first_period"),
            F.min(F.when(F.col("is_repurchase_period") == 1, F.col("period_index"))).alias("second_period"),
            F.sum("revenue").alias("user_revenue"),
        )
        .filter(F.col("second_period").isNotNull())
        .withColumn(
            "bucket",
            F.when(F.col("second_period") == 0, F.lit("same_month"))
            .when(F.col("second_period") == 1, F.lit("month_1"))
            .when(F.col("second_period") == 2, F.lit("month_2"))
            .otherwise(F.lit("month_3_plus")),
        )
    )
    total = max(user_periods.count(), 1)
    return (
        user_periods.groupBy("bucket")
        .agg(F.countDistinct("user_id").alias("users"), F.round(F.avg("user_revenue"), 2).alias("avg_revenue"))
        .withColumn("share", F.round(F.col("users") / F.lit(float(total)), 6))
        .withColumn("contract_version", F.lit(COHORT_CONTRACT_VERSION))
        .select("contract_version", "bucket", "users", "share", "avg_revenue")
        .orderBy("bucket")
    )


def build_cohort_segments(user_cycles: DataFrame, config: dict[str, Any]) -> DataFrame:
    users = (
        user_cycles.groupBy("cohort", "first_category_level1", "user_id")
        .agg(
            F.sum("revenue").alias("user_revenue"),
            F.max("is_repurchase_period").alias("has_repurchase"),
        )
    )
    return (
        users.groupBy("cohort", "first_category_level1")
        .agg(
            F.countDistinct("user_id").alias("users"),
            F.countDistinct(F.when(F.col("has_repurchase") == 1, F.col("user_id"))).alias("repeat_purchase_users"),
            F.round(F.sum("user_revenue"), 2).alias("revenue"),
        )
        .withColumn("repeat_purchase_rate", F.round(F.col("repeat_purchase_users") / F.when(F.col("users") == 0, None).otherwise(F.col("users")), 6))
        .withColumn(
            "risk_level",
            F.when(F.col("users") < int(config["min_cohort_users"]), F.lit("medium"))
            .when(F.col("repeat_purchase_rate") < 0.05, F.lit("high"))
            .otherwise(F.lit("low")),
        )
        .withColumn(
            "reason_codes",
            F.when(F.col("users") < int(config["min_cohort_users"]), F.array(F.lit("sparse_cohort")))
            .when(F.col("repeat_purchase_rate") < 0.05, F.array(F.lit("low_repeat_purchase_rate")))
            .otherwise(F.array(F.lit("stable_repeat_purchase"))),
        )
        .withColumn(
            "recommended_action",
            F.when(F.col("risk_level") == "high", F.lit("Review onboarding, category recommendations, and post-purchase journeys for this cohort."))
            .when(F.col("risk_level") == "medium", F.lit("Treat this cohort as directional until more users accumulate."))
            .otherwise(F.lit("Use this cohort as a repeat-purchase benchmark.")),
        )
        .withColumn("contract_version", F.lit(COHORT_CONTRACT_VERSION))
        .withColumnRenamed("first_category_level1", "category_level1")
        .withColumn("segment_id", F.concat(F.col("cohort"), F.lit(":"), F.col("category_level1")))
        .select(
            "contract_version",
            "segment_id",
            "cohort",
            "category_level1",
            "users",
            "repeat_purchase_users",
            "repeat_purchase_rate",
            "revenue",
            "risk_level",
            "reason_codes",
            "recommended_action",
        )
        .orderBy(F.desc("revenue"), F.desc("users"))
    )


def build_quality(
    user_first: DataFrame,
    retention: DataFrame,
    intervals: DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    agg = user_first.agg(
        F.countDistinct("user_id").alias("purchase_user_count"),
        F.countDistinct("cohort").alias("cohort_count"),
        F.min("first_purchase_date").alias("min_date"),
        F.max("first_purchase_date").alias("max_date"),
    ).collect()[0].asDict()
    min_date = agg.get("min_date")
    max_date = agg.get("max_date")
    history_days = (max_date - min_date).days + 1 if min_date and max_date else 0
    incomplete_cohorts = _incomplete_tail_cohorts(user_first, config)
    excluded = list(incomplete_cohorts)
    retention_for_sparse = retention
    if excluded:
        retention_for_sparse = retention_for_sparse.filter(~F.col("cohort").isin(excluded))
    sparse_cohorts = [
        row["cohort"]
        for row in (
            retention_for_sparse.filter(F.col("cohort_users") < int(config["min_cohort_users"]))
            .select("cohort")
            .distinct()
            .orderBy("cohort")
            .collect()
        )
    ]
    stats = retention.agg(
        F.max("period_index").alias("max_observed_period"),
        F.min(F.when(~F.col("cohort").isin(excluded), F.col("cohort_users"))).alias("min_observed_cohort_users"),
    ).first()
    max_observed_period = int(stats["max_observed_period"]) if stats and stats["max_observed_period"] is not None else -1
    min_observed_cohort_users = (
        int(stats["min_observed_cohort_users"]) if stats and stats["min_observed_cohort_users"] is not None else 0
    )
    interval_count = intervals.count()
    expected_followup_period = min(1, int(config["max_period_index"]))
    checks = [
        {
            "name": "cohort_count",
            "actual": int(agg.get("cohort_count") or 0),
            "operator": ">=",
            "expected": 1,
            "passed": int(agg.get("cohort_count") or 0) >= 1,
        },
        {
            "name": "min_cohort_users",
            "actual": min_observed_cohort_users,
            "operator": ">=",
            "expected": int(config["min_cohort_users"]),
            "passed": not sparse_cohorts,
        },
        {
            "name": "followup_periods",
            "actual": max_observed_period,
            "operator": ">=",
            "expected": expected_followup_period,
            "passed": max_observed_period >= expected_followup_period,
        },
        {
            "name": "repurchase_interval_rows",
            "actual": int(interval_count),
            "operator": ">",
            "expected": 0,
            "passed": interval_count > 0,
        },
    ]
    warnings = []
    if sparse_cohorts:
        warnings.append("sparse_cohorts")
    if max_observed_period < expected_followup_period:
        warnings.append("insufficient_followup_periods")
    if not interval_count:
        warnings.append("empty_repurchase_intervals")
    return {
        "contract_version": COHORT_CONTRACT_VERSION,
        "quality_status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "passed": all(check["passed"] for check in checks),
        "history_days": int(history_days),
        "cohort_count": int(agg.get("cohort_count") or 0),
        "min_cohort_users": int(config["min_cohort_users"]),
        "sparse_cohorts": sparse_cohorts,
        "incomplete_cohorts": sorted(incomplete_cohorts),
        "warnings": warnings,
        "checks": checks,
    }


def _incomplete_tail_cohorts(user_first: DataFrame, config: dict[str, Any]) -> set[str]:
    row = user_first.agg(
        F.max("first_purchase_date").alias("max_date"),
        F.countDistinct("cohort").alias("cohort_count"),
    ).first()
    max_date = row["max_date"] if row else None
    if not max_date or int(row["cohort_count"] or 0) < 2:
        return set()

    latest_cohort = f"{max_date.year:04d}-{max_date.month:02d}"
    month_start = max_date.replace(day=1)
    observed_days = (max_date - month_start).days + 1
    if observed_days >= int(config["min_cohort_observation_days"]):
        return set()
    return {latest_cohort}


def build_summary(
    user_first: DataFrame,
    user_cycles: DataFrame,
    intervals: DataFrame,
    high_risk_count: int,
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    user_stats = user_cycles.groupBy("user_id").agg(F.sum("purchase_count").alias("purchase_count"), F.sum("revenue").alias("revenue"))
    stats = user_stats.agg(
        F.countDistinct("user_id").alias("purchase_user_count"),
        F.countDistinct(F.when(F.col("purchase_count") >= 2, F.col("user_id"))).alias("repeat_purchase_user_count"),
        F.round(F.avg("revenue"), 2).alias("avg_revenue_per_purchase_user"),
        F.round(F.sum("revenue"), 2).alias("cohort_revenue"),
    ).collect()[0].asDict()
    purchase_user_count = int(stats.get("purchase_user_count") or 0)
    repeat_count = int(stats.get("repeat_purchase_user_count") or 0)
    median_bucket = first_interval_bucket(intervals)
    return {
        "contract_version": COHORT_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "cohort_unit": config["cohort_unit"],
        "user_count": int(user_first.select("user_id").distinct().count()),
        "purchase_user_count": purchase_user_count,
        "repeat_purchase_user_count": repeat_count,
        "repeat_purchase_rate": round(repeat_count / purchase_user_count, 6) if purchase_user_count else 0.0,
        "median_days_to_second_purchase": median_bucket,
        "avg_revenue_per_purchase_user": float(stats.get("avg_revenue_per_purchase_user") or 0),
        "cohort_revenue": float(stats.get("cohort_revenue") or 0),
        "high_risk_cohort_count": high_risk_count,
        "quality_status": quality["quality_status"],
        "sparse_cohorts": quality["sparse_cohorts"],
        "recommended_action": "Use cohort retention and repeat purchase curves to prioritize lifecycle and category recovery plays.",
    }


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}


def collect_preview(frame: DataFrame, limit: int) -> list[dict[str, Any]]:
    return [_row_to_dict(row.asDict(recursive=True)) for row in frame.limit(limit).collect()]


def first_interval_bucket(intervals: DataFrame) -> str:
    rows = intervals.orderBy("bucket").limit(1).collect()
    return rows[0]["bucket"] if rows else "none"


def _create_frame(spark: SparkSession, rows: list[dict[str, Any]], schema: T.StructType) -> DataFrame:
    return spark.createDataFrame(rows, schema=schema)
