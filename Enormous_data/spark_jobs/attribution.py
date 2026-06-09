from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import Window
from pyspark.sql import functions as F


ATTRIBUTION_CONTRACT_VERSION = "revenue-attribution/v1"

DEFAULT_CONFIG = {
    "preview_limit": 120,
    "min_purchase_rows": 100,
    "min_attribution_coverage_rate": 0.5,
    "time_decay_base": 0.7,
    "top_paths": 80,
}


def attribution_config(config: dict[str, Any] | None) -> dict[str, Any]:
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


def build_attribution_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    enriched = enrich_events(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    touchpoints = build_purchase_touchpoints(enriched, config).persist(StorageLevel.MEMORY_AND_DISK)
    entities = build_entity_attribution(touchpoints, enriched, config).persist(StorageLevel.MEMORY_AND_DISK)
    models = build_model_summary(entities).persist(StorageLevel.MEMORY_AND_DISK)
    paths = build_path_patterns(enriched, config).persist(StorageLevel.MEMORY_AND_DISK)
    assists = build_assist_opportunities(entities, config).persist(StorageLevel.MEMORY_AND_DISK)

    preview_limit = int(config["preview_limit"])
    entity_rows = [_row_to_dict(row.asDict(recursive=True)) for row in entities.limit(preview_limit).collect()]
    model_rows = [_row_to_dict(row.asDict(recursive=True)) for row in models.collect()]
    path_rows = [_row_to_dict(row.asDict(recursive=True)) for row in paths.collect()]
    assist_rows = [_row_to_dict(row.asDict(recursive=True)) for row in assists.collect()]
    quality = build_quality(enriched, touchpoints, config)
    summary = build_summary(enriched, touchpoints, entities, assists, quality, run_id, input_snapshot)

    enriched.unpersist()
    models.unpersist()
    return (
        {
            "session_touchpoints": touchpoints,
            "entity_attribution": entities,
            "path_patterns": paths,
            "assist_opportunities": assists,
        },
        {
            "attribution_summary": summary,
            "attribution_models": model_rows,
            "attribution_entities": entity_rows[:preview_limit],
            "attribution_paths": path_rows[: int(config["top_paths"])],
            "attribution_assists": assist_rows[:preview_limit],
            "attribution_quality": quality,
        },
    )


def enrich_events(cleaned_df: DataFrame) -> DataFrame:
    return (
        cleaned_df.withColumn("product_id", F.col("product_id").cast("string"))
        .withColumn("user_session", F.col("user_session").cast("string"))
        .withColumn("user_id", F.col("user_id").cast("string"))
        .withColumn("category_level1", F.coalesce(F.col("category_level1"), F.lit("unknown")))
        .withColumn("brand", F.coalesce(F.col("brand"), F.lit("unknown")))
    )


def build_purchase_touchpoints(enriched: DataFrame, config: dict[str, Any]) -> DataFrame:
    purchases = (
        enriched.filter(F.col("event_type") == "purchase")
        .select(
            F.sha2(
                F.concat_ws(
                    "||",
                    F.col("user_session"),
                    F.col("product_id"),
                    F.date_format("event_timestamp", "yyyy-MM-dd HH:mm:ss.SSS"),
                    F.coalesce(F.col("price").cast("string"), F.lit("0")),
                ),
                256,
            ).alias("purchase_id"),
            F.col("user_session"),
            F.col("user_id"),
            F.col("event_timestamp").alias("purchase_ts"),
            F.col("product_id").alias("purchase_product_id"),
            F.col("category_level1").alias("purchase_category_level1"),
            F.col("brand").alias("purchase_brand"),
            F.coalesce(F.col("price"), F.lit(0.0)).alias("purchase_revenue"),
        )
        .filter(F.col("user_session").isNotNull())
    )
    touches = (
        enriched.filter(F.col("event_type").isin("view", "cart", "remove_from_cart"))
        .select(
            F.col("user_session"),
            F.col("event_timestamp").alias("touch_ts"),
            F.col("event_type").alias("touch_event_type"),
            F.col("product_id"),
            F.col("category_level1"),
            F.col("brand"),
        )
        .filter(F.col("user_session").isNotNull())
    )
    joined = purchases.join(touches, ["user_session"], "inner").where(F.col("touch_ts") <= F.col("purchase_ts"))
    by_purchase = Window.partitionBy("purchase_id")
    asc = Window.partitionBy("purchase_id").orderBy("touch_ts", "touch_event_type", "product_id")
    desc = Window.partitionBy("purchase_id").orderBy(F.col("touch_ts").desc(), F.col("touch_event_type").desc(), F.col("product_id").desc())
    decay_base = float(config["time_decay_base"])
    weighted = (
        joined.withColumn("touch_count", F.count("*").over(by_purchase))
        .withColumn("position_before_purchase", F.row_number().over(asc))
        .withColumn("reverse_position_before_purchase", F.row_number().over(desc))
        .withColumn("linear_credit", F.round(F.col("purchase_revenue") / F.col("touch_count"), 6))
        .withColumn("first_touch_credit", F.when(F.col("position_before_purchase") == 1, F.col("purchase_revenue")).otherwise(F.lit(0.0)))
        .withColumn("last_touch_credit", F.when(F.col("reverse_position_before_purchase") == 1, F.col("purchase_revenue")).otherwise(F.lit(0.0)))
        .withColumn("time_decay_weight", F.pow(F.lit(decay_base), F.col("reverse_position_before_purchase") - F.lit(1)))
        .withColumn("time_decay_weight_sum", F.sum("time_decay_weight").over(by_purchase))
        .withColumn("time_decay_credit", F.round(F.col("purchase_revenue") * F.col("time_decay_weight") / F.col("time_decay_weight_sum"), 6))
        .withColumn("minutes_before_purchase", F.round((F.col("purchase_ts").cast("long") - F.col("touch_ts").cast("long")) / 60, 3))
        .withColumn("contract_version", F.lit(ATTRIBUTION_CONTRACT_VERSION))
    )
    return weighted.select(
        "contract_version",
        "purchase_id",
        "user_session",
        "user_id",
        "purchase_ts",
        "purchase_product_id",
        "purchase_category_level1",
        "purchase_brand",
        "purchase_revenue",
        "touch_ts",
        "touch_event_type",
        "product_id",
        "category_level1",
        "brand",
        "touch_count",
        "position_before_purchase",
        "reverse_position_before_purchase",
        "minutes_before_purchase",
        "first_touch_credit",
        "last_touch_credit",
        "linear_credit",
        "time_decay_credit",
    )


def entity_projection(touchpoints: DataFrame, entity_type: str, id_column: str, label_column: str | None = None) -> DataFrame:
    label = F.col(label_column or id_column).cast("string")
    return touchpoints.select(
        "purchase_id",
        "user_session",
        "touch_event_type",
        "purchase_revenue",
        "minutes_before_purchase",
        "position_before_purchase",
        F.lit(entity_type).alias("entity_type"),
        F.col(id_column).cast("string").alias("entity_id"),
        label.alias("entity_label"),
        "first_touch_credit",
        "last_touch_credit",
        "linear_credit",
        "time_decay_credit",
    )


def direct_projection(enriched: DataFrame, entity_type: str, id_column: str, label_column: str | None = None) -> DataFrame:
    label = F.col(label_column or id_column).cast("string")
    return (
        enriched.filter(F.col("event_type") == "purchase")
        .groupBy(F.lit(entity_type).alias("entity_type"), F.col(id_column).cast("string").alias("entity_id"), label.alias("entity_label"))
        .agg(
            F.countDistinct("user_session").alias("direct_purchase_sessions"),
            F.round(F.sum(F.coalesce(F.col("price"), F.lit(0.0))), 6).alias("direct_revenue"),
        )
    )


def build_entity_attribution(touchpoints: DataFrame, enriched: DataFrame, config: dict[str, Any]) -> DataFrame:
    touch_entities = (
        entity_projection(touchpoints, "product", "product_id")
        .unionByName(entity_projection(touchpoints, "brand", "brand"))
        .unionByName(entity_projection(touchpoints, "category", "category_level1"))
    )
    touch_agg = (
        touch_entities.groupBy("entity_type", "entity_id", "entity_label")
        .agg(
            F.countDistinct("user_session").alias("touch_sessions"),
            F.countDistinct("purchase_id").alias("assisted_purchase_sessions"),
            F.round(F.sum("first_touch_credit"), 6).alias("first_touch_revenue"),
            F.round(F.sum("last_touch_credit"), 6).alias("last_touch_revenue"),
            F.round(F.sum("linear_credit"), 6).alias("linear_assisted_revenue"),
            F.round(F.sum("time_decay_credit"), 6).alias("time_decay_assisted_revenue"),
            F.round(F.avg("position_before_purchase"), 3).alias("avg_position_before_purchase"),
            F.round(F.avg("minutes_before_purchase"), 3).alias("avg_minutes_before_purchase"),
            F.sum(F.when(F.col("touch_event_type") == "cart", 1).otherwise(0)).alias("cart_touchpoints"),
            F.sum(F.when(F.col("touch_event_type") == "view", 1).otherwise(0)).alias("view_touchpoints"),
            F.sum(F.when(F.col("touch_event_type") == "remove_from_cart", 1).otherwise(0)).alias("remove_negative_signal_count"),
        )
    )
    direct = (
        direct_projection(enriched, "product", "product_id")
        .unionByName(direct_projection(enriched, "brand", "brand"))
        .unionByName(direct_projection(enriched, "category", "category_level1"))
    )
    ranked = Window.orderBy(F.desc("time_decay_assisted_revenue"), F.desc("linear_assisted_revenue"), F.desc("touch_sessions"))
    min_purchase_rows = float(config["min_purchase_rows"])
    return (
        touch_agg.join(direct, ["entity_type", "entity_id", "entity_label"], "left")
        .fillna({"direct_purchase_sessions": 0, "direct_revenue": 0.0})
        .withColumn("assist_to_direct_ratio", _safe_divide(F.col("time_decay_assisted_revenue"), F.col("direct_revenue")))
        .withColumn("assist_rate", _safe_divide(F.col("assisted_purchase_sessions"), F.col("touch_sessions")))
        .withColumn("confidence", F.round(F.least(F.col("assisted_purchase_sessions") / F.lit(min_purchase_rows), F.lit(1.0)), 6))
        .withColumn(
            "reason_codes",
            F.array_remove(
                F.array(
                    F.when(F.col("assist_to_direct_ratio") >= 1.5, F.lit("high_assist_ratio")),
                    F.when(F.col("cart_touchpoints") > F.col("view_touchpoints"), F.lit("cart_assist_driver")),
                    F.when(F.col("remove_negative_signal_count") > 0, F.lit("contains_remove_signal")),
                    F.lit("multi_touch_driver"),
                ),
                None,
            ),
        )
        .withColumn("rank", F.row_number().over(ranked))
        .withColumn("contract_version", F.lit(ATTRIBUTION_CONTRACT_VERSION))
        .select(
            "contract_version",
            "rank",
            "entity_type",
            "entity_id",
            "entity_label",
            "touch_sessions",
            "assisted_purchase_sessions",
            "direct_purchase_sessions",
            "first_touch_revenue",
            "last_touch_revenue",
            "linear_assisted_revenue",
            "time_decay_assisted_revenue",
            "direct_revenue",
            "assist_to_direct_ratio",
            "assist_rate",
            "avg_position_before_purchase",
            "avg_minutes_before_purchase",
            "cart_touchpoints",
            "view_touchpoints",
            "remove_negative_signal_count",
            "confidence",
            "reason_codes",
        )
        .orderBy("rank")
    )


def build_model_summary(entities: DataFrame) -> DataFrame:
    return (
        entities.groupBy("entity_type")
        .agg(
            F.count("*").alias("entity_count"),
            F.round(F.sum("first_touch_revenue"), 6).alias("first_touch_revenue"),
            F.round(F.sum("last_touch_revenue"), 6).alias("last_touch_revenue"),
            F.round(F.sum("linear_assisted_revenue"), 6).alias("linear_assisted_revenue"),
            F.round(F.sum("time_decay_assisted_revenue"), 6).alias("time_decay_assisted_revenue"),
            F.round(F.sum("direct_revenue"), 6).alias("direct_revenue"),
        )
        .withColumn("contract_version", F.lit(ATTRIBUTION_CONTRACT_VERSION))
        .select(
            "contract_version",
            "entity_type",
            "entity_count",
            "first_touch_revenue",
            "last_touch_revenue",
            "linear_assisted_revenue",
            "time_decay_assisted_revenue",
            "direct_revenue",
        )
        .orderBy("entity_type")
    )


def build_path_patterns(enriched: DataFrame, config: dict[str, Any]) -> DataFrame:
    events = enriched.filter(F.col("user_session").isNotNull()).select("user_session", "event_timestamp", "event_type", "price")
    session_paths = (
        events.groupBy("user_session")
        .agg(
            F.array_join(F.transform(F.sort_array(F.collect_list(F.struct("event_timestamp", "event_type"))), lambda x: x["event_type"]), ">").alias("path_pattern"),
            F.max(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("has_purchase"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0.0))).otherwise(F.lit(0.0))), 6).alias("revenue"),
            F.min("event_timestamp").alias("session_start"),
            F.max(F.when(F.col("event_type") == "purchase", F.col("event_timestamp"))).alias("last_purchase_ts"),
        )
        .withColumn("latency_minutes", F.round((F.col("last_purchase_ts").cast("long") - F.col("session_start").cast("long")) / 60, 3))
    )
    return (
        session_paths.groupBy("path_pattern")
        .agg(
            F.count("*").alias("sessions"),
            F.sum("has_purchase").alias("purchase_sessions"),
            F.round(F.sum("revenue"), 6).alias("revenue"),
            F.expr("percentile_approx(latency_minutes, 0.5)").alias("median_latency_minutes"),
        )
        .withColumn("conversion_rate", _safe_divide(F.col("purchase_sessions"), F.col("sessions")))
        .withColumn("sample_size", F.col("sessions"))
        .withColumn("contract_version", F.lit(ATTRIBUTION_CONTRACT_VERSION))
        .select(
            "contract_version",
            "path_pattern",
            "sessions",
            "purchase_sessions",
            "revenue",
            "conversion_rate",
            "median_latency_minutes",
            "sample_size",
        )
        .orderBy(F.desc("revenue"), F.desc("purchase_sessions"))
        .limit(int(config["top_paths"]))
    )


def build_assist_opportunities(entities: DataFrame, config: dict[str, Any]) -> DataFrame:
    return (
        entities.withColumn(
            "suggested_action",
            F.when(F.col("assist_to_direct_ratio") >= 2, F.lit("strengthen_recommendation_exposure"))
            .when(F.col("cart_touchpoints") >= F.col("view_touchpoints"), F.lit("promote_cart_assist_path"))
            .otherwise(F.lit("monitor_assist_entity")),
        )
        .withColumn("priority_score", F.round(F.col("time_decay_assisted_revenue") * F.coalesce(F.col("confidence"), F.lit(0)), 4))
        .filter(F.col("priority_score") > 0)
        .select(
            "contract_version",
            "entity_type",
            "entity_id",
            "entity_label",
            "suggested_action",
            "priority_score",
            "confidence",
            "time_decay_assisted_revenue",
            "linear_assisted_revenue",
            "direct_revenue",
            "assist_to_direct_ratio",
            "assisted_purchase_sessions",
            "touch_sessions",
            "reason_codes",
        )
        .orderBy(F.desc("priority_score"), F.desc("confidence"))
        .limit(int(config["preview_limit"]))
    )


def build_quality(enriched: DataFrame, touchpoints: DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    purchase_rows = enriched.filter(F.col("event_type") == "purchase").count()
    purchase_sessions = enriched.filter(F.col("event_type") == "purchase").select("user_session").distinct().count()
    attributable_sessions = touchpoints.select("user_session").distinct().count()
    session_missing_rows = enriched.filter(F.col("user_session").isNull()).count()
    rows = enriched.count()
    valid_purchase_price_rows = enriched.filter((F.col("event_type") == "purchase") & (F.col("price") > 0)).count()
    history_days = enriched.select(F.to_date("event_timestamp").alias("dt")).where(F.col("dt").isNotNull()).distinct().count()
    coverage = round(attributable_sessions / purchase_sessions, 6) if purchase_sessions else 0.0
    warnings: list[str] = []
    status = "passed"
    if purchase_rows == 0:
        status = "failed"
        warnings.append("no_purchase_rows")
    if purchase_rows < int(config["min_purchase_rows"]):
        warnings.append("low_purchase_rows")
    if coverage < float(config["min_attribution_coverage_rate"]):
        warnings.append("low_attribution_coverage")
    if history_days < 2:
        warnings.append("history_days")
    if warnings and status != "failed":
        status = "needs_review"
    return {
        "contract_version": ATTRIBUTION_CONTRACT_VERSION,
        "quality_status": status,
        "purchase_rows": purchase_rows,
        "purchase_sessions": purchase_sessions,
        "attributable_sessions": attributable_sessions,
        "attribution_coverage_rate": coverage,
        "session_missing_rate": round(session_missing_rows / rows, 6) if rows else 0.0,
        "valid_purchase_price_rate": round(valid_purchase_price_rows / purchase_rows, 6) if purchase_rows else 0.0,
        "history_days": history_days,
        "warnings": warnings,
    }


def build_summary(
    enriched: DataFrame,
    touchpoints: DataFrame,
    entities: DataFrame,
    assists: DataFrame,
    quality: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    purchase = enriched.filter(F.col("event_type") == "purchase")
    row = purchase.agg(
        F.count("*").alias("purchase_rows"),
        F.countDistinct("user_session").alias("purchase_sessions"),
        F.round(F.sum(F.coalesce(F.col("price"), F.lit(0.0))), 6).alias("total_purchase_revenue"),
    ).first()
    purchase_touch_summary = touchpoints.select("purchase_id", "user_session", "touch_count").distinct()
    touch_row = purchase_touch_summary.agg(
        F.countDistinct("purchase_id").alias("attributable_purchases"),
        F.round(F.avg("touch_count"), 3).alias("avg_touchpoints_before_purchase"),
    ).first()
    minutes_row = touchpoints.agg(F.round(F.avg("minutes_before_purchase"), 3).alias("avg_minutes_before_purchase")).first()
    entity_summary = entities.agg(
        F.count("*").alias("entity_count"),
        F.round(
            F.sum(F.when(F.col("entity_type") == "category", F.coalesce(F.col("time_decay_assisted_revenue"), F.lit(0.0))).otherwise(F.lit(0.0))),
            6,
        ).alias("assisted_revenue"),
    ).first()
    purchase_sessions = int(row["purchase_sessions"] or 0)
    attributable_sessions = int(quality["attributable_sessions"])
    return {
        "contract_version": ATTRIBUTION_CONTRACT_VERSION,
        "run_id": run_id,
        "quality_status": quality["quality_status"],
        "configured_input_path": input_snapshot["configured_input_path"],
        "actual_input_path": input_snapshot["actual_input_path"],
        "purchase_rows": int(row["purchase_rows"] or 0),
        "purchase_sessions": purchase_sessions,
        "attributable_sessions": attributable_sessions,
        "attributable_purchases": int(touch_row["attributable_purchases"] or 0),
        "attribution_coverage_rate": quality["attribution_coverage_rate"],
        "total_purchase_revenue": float(row["total_purchase_revenue"] or 0),
        "assisted_revenue": float(entity_summary["assisted_revenue"] or 0),
        "avg_touchpoints_before_purchase": float(touch_row["avg_touchpoints_before_purchase"] or 0),
        "avg_minutes_before_purchase": float(minutes_row["avg_minutes_before_purchase"] or 0),
        "multi_touch_purchase_rate": round(
            purchase_touch_summary.filter(F.col("touch_count") > 1).count() / max(int(touch_row["attributable_purchases"] or 0), 1),
            6,
        ),
        "entity_count": int(entity_summary["entity_count"] or 0),
        "assist_opportunity_count": assists.count(),
        "warnings": quality["warnings"],
    }
