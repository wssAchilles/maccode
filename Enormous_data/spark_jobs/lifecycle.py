from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


LIFECYCLE_CONTRACT_VERSION = "customer-lifecycle-intelligence/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "high_value_revenue": 500.0,
    "loyal_purchase_days": 2,
    "active_days": 3,
    "at_risk_recency_days": 14,
    "champion_min_revenue": 1000.0,
    "champion_min_purchase_days": 2,
}


def lifecycle_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_lifecycle_outputs(
    daily_user: DataFrame,
    daily_category: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    users = build_user_lifecycle(daily_user, config, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    segment_distribution = build_segment_distribution(users)
    category_affinity = build_category_affinity(users, daily_category, int(config["preview_limit"]))
    risk_queue = build_risk_queue(users, int(config["preview_limit"]))
    summary = build_lifecycle_summary(users, segment_distribution, run_id, config)
    rules = build_rules(config)

    frames = {
        "user_lifecycle": users,
        "segment_distribution": daily_user.sparkSession.createDataFrame(segment_distribution),
    }
    metrics = {
        "lifecycle_summary": summary,
        "lifecycle_segments": segment_distribution,
        "lifecycle_risk_queue": risk_queue,
        "lifecycle_category_affinity": category_affinity,
        "lifecycle_rules": rules,
    }
    return frames, metrics


def build_user_lifecycle(daily_user: DataFrame, config: dict[str, Any], run_id: str) -> DataFrame:
    max_dt = daily_user.agg(F.max("dt").alias("max_dt")).first()["max_dt"]
    base = (
        daily_user.groupBy("user_id")
        .agg(
            F.countDistinct("dt").alias("active_days"),
            F.sum("sessions").alias("sessions"),
            F.sum("views").alias("views"),
            F.sum("carts").alias("carts"),
            F.sum("purchases").alias("purchases"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.countDistinct(F.when(F.col("purchases") > 0, F.col("dt"))).alias("purchase_days"),
            F.max("dt").alias("last_active_dt"),
            F.max(F.when(F.col("purchases") > 0, F.col("dt"))).alias("last_purchase_dt"),
            F.max_by("preferred_category_level1", "dt").alias("preferred_category_level1"),
            F.sum("distinct_products").alias("product_touch_count"),
            F.sum("distinct_categories").alias("category_touch_count"),
        )
        .withColumn("snapshot_dt", F.lit(max_dt))
        .withColumn("recency_days", F.datediff(F.to_date(F.lit(max_dt)), F.to_date("last_active_dt")))
        .withColumn(
            "purchase_recency_days",
            F.when(F.col("last_purchase_dt").isNull(), None).otherwise(F.datediff(F.to_date(F.lit(max_dt)), F.to_date("last_purchase_dt"))),
        )
        .withColumn("avg_order_value", F.round(F.col("revenue") / F.when(F.col("purchases") == 0, None).otherwise(F.col("purchases")), 2))
        .withColumn("view_to_purchase_rate", F.round(F.col("purchases") / F.when(F.col("views") == 0, None).otherwise(F.col("views")), 6))
        .withColumn("monetary_score", F.when(F.col("revenue") >= float(config["high_value_revenue"]), 3).when(F.col("revenue") > 0, 2).otherwise(1))
        .withColumn(
            "frequency_score",
            F.when(F.col("purchase_days") >= int(config["loyal_purchase_days"]), 3).when(F.col("purchases") > 0, 2).otherwise(1),
        )
        .withColumn("recency_score", F.when(F.col("recency_days") <= 1, 3).when(F.col("recency_days") <= 7, 2).otherwise(1))
    )
    return (
        base.withColumn(
            "lifecycle_segment",
            F.when(
                (F.col("revenue") >= float(config["champion_min_revenue"]))
                & (F.col("purchase_days") >= int(config["champion_min_purchase_days"])),
                F.lit("champion"),
            )
            .when((F.col("revenue") >= float(config["high_value_revenue"])) & (F.col("purchases") > 0), F.lit("high_value"))
            .when(F.col("purchase_days") >= int(config["loyal_purchase_days"]), F.lit("loyal"))
            .when(F.col("purchases") > 0, F.lit("buyer"))
            .when(F.col("carts") > 0, F.lit("cart_intent"))
            .when(F.col("views") > 0, F.lit("browser"))
            .otherwise(F.lit("unknown")),
        )
        .withColumn(
            "risk_band",
            F.when(F.col("recency_days") >= int(config["at_risk_recency_days"]), F.lit("at_risk"))
            .when((F.col("purchases") == 0) & (F.col("carts") > 0), F.lit("convert_intent"))
            .when(F.col("purchases") > 0, F.lit("active_value"))
            .otherwise(F.lit("observe")),
        )
        .withColumn(
            "recommended_action",
            F.when(F.col("risk_band") == "at_risk", F.lit("Reactivate with category-personalized offers and inspect recommendation coverage."))
            .when(F.col("risk_band") == "convert_intent", F.lit("Prioritize cart recovery and compare price or availability friction."))
            .when(F.col("lifecycle_segment").isin("champion", "high_value"), F.lit("Protect experience quality and avoid excessive fallback recommendations."))
            .otherwise(F.lit("Keep monitoring behavior until stronger purchase evidence appears.")),
        )
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(LIFECYCLE_CONTRACT_VERSION))
    )


def build_segment_distribution(users: DataFrame) -> list[dict[str, Any]]:
    rows = (
        users.groupBy("lifecycle_segment")
        .agg(
            F.count("*").alias("users"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.sum("purchases").alias("purchases"),
            F.round(F.avg("recency_days"), 2).alias("avg_recency_days"),
        )
        .orderBy(F.desc("revenue"), F.desc("users"))
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def build_risk_queue(users: DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = (
        users.filter(F.col("risk_band").isin("at_risk", "convert_intent", "active_value"))
        .orderBy(F.desc("revenue"), F.desc("carts"), F.desc("views"), F.asc("user_id"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def build_category_affinity(users: DataFrame, daily_category: DataFrame, limit: int) -> list[dict[str, Any]]:
    category_revenue = daily_category.groupBy("category_level1").agg(
        F.round(F.sum("revenue"), 2).alias("category_revenue"),
        F.sum("purchases").alias("category_purchases"),
    )
    rows = (
        users.groupBy("preferred_category_level1")
        .agg(
            F.count("*").alias("users"),
            F.round(F.sum("revenue"), 2).alias("user_revenue"),
            F.sum("purchases").alias("user_purchases"),
        )
        .withColumnRenamed("preferred_category_level1", "category_level1")
        .join(category_revenue, on="category_level1", how="left")
        .orderBy(F.desc("user_revenue"), F.desc("users"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def build_lifecycle_summary(
    users: DataFrame,
    segments: list[dict[str, Any]],
    run_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    row = users.agg(
        F.count("*").alias("user_count"),
        F.sum("purchases").alias("purchase_count"),
        F.round(F.sum("revenue"), 2).alias("revenue"),
        F.sum(F.when(F.col("risk_band") == "at_risk", 1).otherwise(0)).alias("at_risk_users"),
        F.sum(F.when(F.col("risk_band") == "convert_intent", 1).otherwise(0)).alias("convert_intent_users"),
        F.sum(F.when(F.col("lifecycle_segment").isin("champion", "high_value"), 1).otherwise(0)).alias("high_value_users"),
        F.round(F.avg("recency_days"), 2).alias("avg_recency_days"),
        F.min("snapshot_dt").alias("snapshot_dt"),
    ).first()
    return {
        "contract_version": LIFECYCLE_CONTRACT_VERSION,
        "run_id": run_id,
        "snapshot_dt": row["snapshot_dt"],
        "user_count": int(row["user_count"] or 0),
        "purchase_count": int(row["purchase_count"] or 0),
        "revenue": float(row["revenue"] or 0),
        "at_risk_users": int(row["at_risk_users"] or 0),
        "convert_intent_users": int(row["convert_intent_users"] or 0),
        "high_value_users": int(row["high_value_users"] or 0),
        "avg_recency_days": float(row["avg_recency_days"] or 0),
        "segment_count": len(segments),
        "top_segment": segments[0] if segments else None,
        "rules": {
            "high_value_revenue": float(config["high_value_revenue"]),
            "loyal_purchase_days": int(config["loyal_purchase_days"]),
            "at_risk_recency_days": int(config["at_risk_recency_days"]),
        },
    }


def build_rules(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": LIFECYCLE_CONTRACT_VERSION,
        "model": "deterministic RFM + engagement segmentation",
        "rules": [
            {"name": "champion", "description": "high revenue and repeated purchase days", "threshold": float(config["champion_min_revenue"])},
            {"name": "high_value", "description": "purchase user above high value revenue threshold", "threshold": float(config["high_value_revenue"])},
            {"name": "loyal", "description": "purchase days above loyalty threshold", "threshold": int(config["loyal_purchase_days"])},
            {"name": "at_risk", "description": "last active day older than risk threshold", "threshold": int(config["at_risk_recency_days"])},
            {"name": "cart_intent", "description": "cart activity exists before purchase evidence", "threshold": 1},
        ],
    }


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
