from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import Window
from pyspark.sql import functions as F


CART_RECOVERY_CONTRACT_VERSION = "cart-recovery-intelligence/v1"

DEFAULT_CONFIG = {
    "preview_limit": 120,
    "min_cart_sessions": 20,
    "min_history_days": 2,
    "high_abandonment_rate": 0.65,
}


def cart_recovery_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def _safe_divide(numerator: F.Column, denominator: F.Column) -> F.Column:
    return F.round(numerator / F.when(denominator == 0, None).otherwise(denominator), 6)


def _row_to_dict(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def build_cart_recovery_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    facts = build_cart_product_facts(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    categories = build_category_segments(facts).persist(StorageLevel.MEMORY_AND_DISK)
    products = build_product_segments(facts, config).persist(StorageLevel.MEMORY_AND_DISK)
    queue = build_recovery_queue(categories, products, config).persist(StorageLevel.MEMORY_AND_DISK)

    preview_limit = int(config["preview_limit"])
    category_rows = [_row_to_dict(row.asDict(recursive=True)) for row in categories.limit(preview_limit).collect()]
    product_rows = [_row_to_dict(row.asDict(recursive=True)) for row in products.limit(preview_limit).collect()]
    queue_rows = [_row_to_dict(row.asDict(recursive=True)) for row in queue.limit(preview_limit).collect()]
    quality = build_quality(cleaned_df, facts, config)
    summary = build_summary(categories, products, queue, product_rows, queue_rows, quality, config, run_id, input_snapshot)

    return (
        {
            "cart_product_facts": facts,
            "cart_category_segments": categories,
            "cart_product_segments": products,
            "cart_recovery_queue": queue,
        },
        {
            "cart_summary": summary,
            "cart_category_segments": category_rows[:preview_limit],
            "cart_product_segments": product_rows[:preview_limit],
            "cart_recovery_queue": queue_rows[:preview_limit],
            "cart_quality": quality,
        },
    )


def build_cart_product_facts(cleaned_df: DataFrame) -> DataFrame:
    cart = F.col("event_type") == "cart"
    remove = F.col("event_type") == "remove_from_cart"
    purchase = F.col("event_type") == "purchase"
    facts = (
        cleaned_df.withColumn("category_level1", F.coalesce(F.col("category_level1"), F.lit("unknown")))
        .withColumn("brand", F.coalesce(F.col("brand"), F.lit("unknown")))
        .groupBy("user_session", "user_id", "product_id", "category_level1", "brand")
        .agg(
            F.min(F.when(cart, F.col("event_timestamp"))).alias("first_cart_ts"),
            F.max(F.when(remove, F.col("event_timestamp"))).alias("last_remove_ts"),
            F.min(F.when(purchase, F.col("event_timestamp"))).alias("first_purchase_ts"),
            F.count(F.when(cart, F.lit(1))).alias("cart_events"),
            F.count(F.when(remove, F.lit(1))).alias("remove_events"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_events"),
            F.round(F.avg(F.when(cart | purchase, F.coalesce(F.col("price"), F.lit(0)))), 2).alias("unit_price"),
            F.to_date(F.min("event_timestamp")).alias("session_date"),
        )
        .filter(F.col("first_cart_ts").isNotNull())
        .withColumn(
            "recovered",
            F.when(F.col("first_purchase_ts").isNotNull() & (F.col("first_purchase_ts") >= F.col("first_cart_ts")), F.lit(1)).otherwise(F.lit(0)),
        )
        .withColumn(
            "explicit_remove",
            F.when(F.col("last_remove_ts").isNotNull() & (F.col("last_remove_ts") >= F.col("first_cart_ts")), F.lit(1)).otherwise(F.lit(0)),
        )
        .withColumn("abandoned", F.when(F.col("recovered") == 0, F.lit(1)).otherwise(F.lit(0)))
        .withColumn("cart_value", F.round(F.coalesce(F.col("unit_price"), F.lit(0)) * F.col("cart_events"), 2))
        .withColumn("abandoned_value", F.round(F.when(F.col("abandoned") == 1, F.col("cart_value")).otherwise(F.lit(0)), 2))
    )
    return facts.select(
        "user_session",
        "user_id",
        F.col("product_id").cast("string").alias("product_id"),
        "category_level1",
        "brand",
        "session_date",
        "cart_events",
        "remove_events",
        "purchase_events",
        "unit_price",
        "cart_value",
        "abandoned_value",
        "recovered",
        "explicit_remove",
        "abandoned",
    )


def build_category_segments(facts: DataFrame) -> DataFrame:
    grouped = (
        facts.groupBy("category_level1")
        .agg(
            F.count("*").alias("cart_product_sessions"),
            F.sum("cart_events").alias("cart_events"),
            F.sum("remove_events").alias("remove_events"),
            F.sum("recovered").alias("recovered_sessions"),
            F.sum("explicit_remove").alias("explicit_remove_sessions"),
            F.sum("abandoned").alias("abandoned_sessions"),
            F.round(F.sum("cart_value"), 2).alias("cart_value"),
            F.round(F.sum("abandoned_value"), 2).alias("abandoned_value"),
        )
        .withColumn("recovery_rate", _safe_divide(F.col("recovered_sessions"), F.col("cart_product_sessions")))
        .withColumn("abandonment_rate", _safe_divide(F.col("abandoned_sessions"), F.col("cart_product_sessions")))
        .withColumn("remove_rate", _safe_divide(F.col("explicit_remove_sessions"), F.col("cart_product_sessions")))
        .withColumn("contract_version", F.lit(CART_RECOVERY_CONTRACT_VERSION))
    )
    return grouped.select(
        "contract_version",
        "category_level1",
        "cart_product_sessions",
        "cart_events",
        "remove_events",
        "recovered_sessions",
        "explicit_remove_sessions",
        "abandoned_sessions",
        "cart_value",
        "abandoned_value",
        "recovery_rate",
        "abandonment_rate",
        "remove_rate",
    ).orderBy(F.desc("abandoned_value"), F.desc("abandoned_sessions"))


def build_product_segments(facts: DataFrame, config: dict[str, Any]) -> DataFrame:
    grouped = (
        facts.groupBy("product_id", "category_level1", "brand")
        .agg(
            F.count("*").alias("cart_product_sessions"),
            F.sum("cart_events").alias("cart_events"),
            F.sum("remove_events").alias("remove_events"),
            F.sum("recovered").alias("recovered_sessions"),
            F.sum("explicit_remove").alias("explicit_remove_sessions"),
            F.sum("abandoned").alias("abandoned_sessions"),
            F.round(F.avg("unit_price"), 2).alias("avg_price"),
            F.round(F.sum("abandoned_value"), 2).alias("abandoned_value"),
        )
        .withColumn("recovery_rate", _safe_divide(F.col("recovered_sessions"), F.col("cart_product_sessions")))
        .withColumn("abandonment_rate", _safe_divide(F.col("abandoned_sessions"), F.col("cart_product_sessions")))
        .withColumn("remove_rate", _safe_divide(F.col("explicit_remove_sessions"), F.col("cart_product_sessions")))
        .withColumn("priority_score", F.round(F.col("abandoned_value") * F.coalesce(F.col("abandonment_rate"), F.lit(0)), 4))
        .withColumn("contract_version", F.lit(CART_RECOVERY_CONTRACT_VERSION))
    )
    ranked = Window.orderBy(F.desc("priority_score"), F.desc("abandoned_sessions"), F.desc("cart_product_sessions"))
    return (
        grouped.withColumn("rank", F.row_number().over(ranked))
        .select(
            "contract_version",
            "rank",
            "product_id",
            "category_level1",
            "brand",
            "cart_product_sessions",
            "cart_events",
            "remove_events",
            "recovered_sessions",
            "explicit_remove_sessions",
            "abandoned_sessions",
            "avg_price",
            "abandoned_value",
            "recovery_rate",
            "abandonment_rate",
            "remove_rate",
            "priority_score",
        )
        .orderBy("rank")
        .limit(int(config["preview_limit"]))
    )


def build_recovery_queue(categories: DataFrame, products: DataFrame, config: dict[str, Any]) -> DataFrame:
    min_sessions = float(config["min_cart_sessions"])
    high_abandonment = float(config["high_abandonment_rate"])
    product_queue = (
        products.withColumn("entity_type", F.lit("product"))
        .withColumn("entity_id", F.col("product_id").cast("string"))
        .withColumn("entity_label", F.concat_ws(" / ", F.col("brand"), F.col("category_level1"), F.col("product_id").cast("string")))
        .withColumn(
            "recovery_action",
            F.when(F.col("remove_rate") >= 0.5, F.lit("inspect_product_friction"))
            .when(F.col("abandonment_rate") >= high_abandonment, F.lit("recovery_offer_or_reminder"))
            .otherwise(F.lit("watch_cart_followup")),
        )
        .withColumn("confidence", F.round(F.least(F.col("cart_product_sessions") / F.lit(min_sessions), F.lit(1.0)), 6))
        .withColumn("reason_codes", F.array(F.col("recovery_action"), F.lit("product_cart_abandonment")))
        .select(
            "contract_version",
            "entity_type",
            "entity_id",
            "entity_label",
            "recovery_action",
            "priority_score",
            "confidence",
            "cart_product_sessions",
            "abandoned_sessions",
            "abandoned_value",
            "abandonment_rate",
            "remove_rate",
            "reason_codes",
        )
    )
    category_queue = (
        categories.withColumn("entity_type", F.lit("category"))
        .withColumn("entity_id", F.col("category_level1"))
        .withColumn("entity_label", F.col("category_level1"))
        .withColumn(
            "recovery_action",
            F.when(F.col("remove_rate") >= 0.5, F.lit("category_merchandising_review"))
            .when(F.col("abandonment_rate") >= high_abandonment, F.lit("category_recovery_campaign"))
            .otherwise(F.lit("category_watch")),
        )
        .withColumn("priority_score", F.round(F.col("abandoned_value") * F.coalesce(F.col("abandonment_rate"), F.lit(0)), 4))
        .withColumn("confidence", F.round(F.least(F.col("cart_product_sessions") / F.lit(min_sessions), F.lit(1.0)), 6))
        .withColumn("reason_codes", F.array(F.col("recovery_action"), F.lit("category_cart_abandonment")))
        .select(
            "contract_version",
            "entity_type",
            "entity_id",
            "entity_label",
            "recovery_action",
            "priority_score",
            "confidence",
            "cart_product_sessions",
            "abandoned_sessions",
            "abandoned_value",
            "abandonment_rate",
            "remove_rate",
            "reason_codes",
        )
    )
    return product_queue.unionByName(category_queue).orderBy(F.desc("priority_score"), F.desc("confidence")).limit(int(config["preview_limit"]))


def build_quality(cleaned_df: DataFrame, facts: DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    cart_event_rows = cleaned_df.filter(F.col("event_type") == "cart").count()
    remove_event_rows = cleaned_df.filter(F.col("event_type") == "remove_from_cart").count()
    cart_product_sessions = facts.count()
    history_days = cleaned_df.select(F.to_date("event_timestamp").alias("dt")).where(F.col("dt").isNotNull()).distinct().count()
    warnings: list[str] = []
    if cart_event_rows == 0:
        warnings.append("no_cart_events")
    if cart_product_sessions < int(config["min_cart_sessions"]):
        warnings.append("low_cart_product_sessions")
    if history_days < int(config["min_history_days"]):
        warnings.append("history_days")
    quality_status = "passed" if not warnings else "needs_review"
    return {
        "contract_version": CART_RECOVERY_CONTRACT_VERSION,
        "quality_status": quality_status,
        "cart_event_rows": cart_event_rows,
        "remove_event_rows": remove_event_rows,
        "cart_product_sessions": cart_product_sessions,
        "history_days": history_days,
        "min_cart_sessions": int(config["min_cart_sessions"]),
        "min_history_days": int(config["min_history_days"]),
        "warnings": warnings,
    }


def build_summary(
    categories: DataFrame,
    products: DataFrame,
    queue: DataFrame,
    product_rows: list[dict[str, Any]],
    queue_rows: list[dict[str, Any]],
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    totals = categories.agg(
        F.sum("cart_product_sessions").alias("cart_product_sessions"),
        F.sum("abandoned_sessions").alias("abandoned_sessions"),
        F.sum("recovered_sessions").alias("recovered_sessions"),
        F.sum("explicit_remove_sessions").alias("explicit_remove_sessions"),
        F.round(F.sum("cart_value"), 2).alias("cart_value"),
        F.round(F.sum("abandoned_value"), 2).alias("abandoned_value"),
        F.count("*").alias("category_count"),
    ).first()
    cart_product_sessions = int(totals["cart_product_sessions"] or 0)
    abandoned_sessions = int(totals["abandoned_sessions"] or 0)
    recovered_sessions = int(totals["recovered_sessions"] or 0)
    explicit_remove_sessions = int(totals["explicit_remove_sessions"] or 0)
    cart_value = float(totals["cart_value"] or 0)
    abandoned_value = float(totals["abandoned_value"] or 0)
    return {
        "contract_version": CART_RECOVERY_CONTRACT_VERSION,
        "run_id": run_id,
        "quality_status": quality["quality_status"],
        "configured_input_path": input_snapshot["configured_input_path"],
        "actual_input_path": input_snapshot["actual_input_path"],
        "cart_product_sessions": cart_product_sessions,
        "abandoned_sessions": abandoned_sessions,
        "recovered_sessions": recovered_sessions,
        "explicit_remove_sessions": explicit_remove_sessions,
        "cart_value": cart_value,
        "abandoned_value": abandoned_value,
        "abandonment_rate": round(abandoned_sessions / cart_product_sessions, 6) if cart_product_sessions else 0.0,
        "recovery_rate": round(recovered_sessions / cart_product_sessions, 6) if cart_product_sessions else 0.0,
        "remove_rate": round(explicit_remove_sessions / cart_product_sessions, 6) if cart_product_sessions else 0.0,
        "category_count": int(totals["category_count"] or 0),
        "product_count": len(product_rows),
        "queue_count": len(queue_rows),
        "product_output_rows": products.count(),
        "queue_output_rows": queue.count(),
        "min_cart_sessions": int(config["min_cart_sessions"]),
        "warnings": quality["warnings"],
    }
