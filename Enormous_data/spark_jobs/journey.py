from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


JOURNEY_CONTRACT_VERSION = "customer-journey-intelligence/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "max_path_events": 8,
    "min_path_sessions": 1,
    "min_transition_count": 1,
}


def journey_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_journey_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    session_paths = build_session_paths(cleaned_df, int(config["max_path_events"])).persist(StorageLevel.MEMORY_AND_DISK)
    transitions = build_transition_facts(session_paths).persist(StorageLevel.MEMORY_AND_DISK)
    paths = collect_top_paths(session_paths, int(config["preview_limit"]), int(config["min_path_sessions"]))
    transition_rows = collect_transitions(transitions, int(config["preview_limit"]), int(config["min_transition_count"]))
    exits = collect_exit_events(session_paths, int(config["preview_limit"]))
    purchase_paths = collect_purchase_paths(session_paths, int(config["preview_limit"]))
    summary = build_summary(session_paths, paths, exits, transition_rows, run_id)

    frames = {
        "session_paths": session_paths,
        "transition_facts": transitions,
    }
    metrics = {
        "journey_summary": summary,
        "journey_paths": paths,
        "journey_transitions": transition_rows,
        "journey_exit_events": exits,
        "journey_purchase_paths": purchase_paths,
    }
    return frames, metrics


def build_session_paths(cleaned_df: DataFrame, max_path_events: int) -> DataFrame:
    event_struct = F.struct(
        F.col("event_timestamp").alias("ts"),
        F.col("event_type").alias("event_type"),
        F.col("product_id").cast("string").alias("product_id"),
        F.col("category_level1").alias("category_level1"),
    )
    base = (
        cleaned_df.filter(F.col("user_session") != "unknown")
        .groupBy("user_session")
        .agg(
            F.first("user_id").cast("string").alias("user_id"),
            F.min("event_timestamp").alias("session_start"),
            F.max("event_timestamp").alias("session_end"),
            F.to_date(F.min("event_timestamp")).alias("session_date"),
            F.sort_array(F.collect_list(event_struct)).alias("event_structs"),
            F.max(F.when(F.col("event_type") == "purchase", F.lit(1)).otherwise(F.lit(0))).alias("has_purchase"),
            F.max(F.when(F.col("event_type") == "cart", F.lit(1)).otherwise(F.lit(0))).alias("has_cart"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias(
                "revenue"
            ),
            F.count("*").alias("event_count"),
            F.countDistinct("product_id").alias("distinct_products"),
            F.countDistinct("category_level1").alias("distinct_categories"),
        )
        .withColumn("events", F.expr("transform(event_structs, x -> x.event_type)"))
        .withColumn("path_events", F.expr(f"slice(events, 1, {max_path_events})"))
        .withColumn("path_signature", F.concat_ws(" → ", F.col("path_events")))
        .withColumn("first_event", F.element_at("events", 1))
        .withColumn("last_event", F.element_at("events", -1))
        .withColumn("step_count", F.size("events"))
        .withColumn("duration_seconds", F.col("session_end").cast("long") - F.col("session_start").cast("long"))
        .withColumn("contract_version", F.lit(JOURNEY_CONTRACT_VERSION))
    )
    return base.drop("event_structs")


def build_transition_facts(session_paths: DataFrame) -> DataFrame:
    transition_source = (
        session_paths.filter(F.size("events") > 1)
        .select(
            "user_session",
            "user_id",
            "has_purchase",
            "revenue",
            F.expr("arrays_zip(slice(events, 1, size(events) - 1), slice(events, 2, size(events) - 1))").alias("pairs"),
        )
        .select("user_session", "user_id", "has_purchase", "revenue", F.explode("pairs").alias("pair"))
        .select(
            "user_session",
            "user_id",
            "has_purchase",
            "revenue",
            F.col("pair.0").alias("from_event"),
            F.col("pair.1").alias("to_event"),
        )
    )
    return (
        transition_source.groupBy("from_event", "to_event")
        .agg(
            F.count("*").alias("transitions"),
            F.countDistinct("user_session").alias("sessions"),
            F.countDistinct(F.when(F.col("has_purchase") == 1, F.col("user_session"))).alias("purchase_sessions"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
        )
        .withColumn("conversion_rate", F.round(F.col("purchase_sessions") / F.col("sessions"), 6))
        .withColumn(
            "dropoff_hint",
            F.when((F.col("to_event") == "remove_from_cart") | (F.col("conversion_rate") < F.lit(0.02)), F.lit("inspect friction"))
            .when(F.col("to_event") == "purchase", F.lit("conversion step"))
            .otherwise(F.lit("normal navigation")),
        )
        .withColumn("contract_version", F.lit(JOURNEY_CONTRACT_VERSION))
    )


def collect_top_paths(session_paths: DataFrame, limit: int, min_sessions: int) -> list[dict[str, Any]]:
    rows = (
        session_paths.groupBy("path_signature")
        .agg(
            F.count("*").alias("sessions"),
            F.sum("has_cart").alias("cart_sessions"),
            F.sum("has_purchase").alias("purchase_sessions"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.round(F.avg("step_count"), 2).alias("avg_steps"),
            F.round(F.avg("duration_seconds"), 2).alias("avg_duration_seconds"),
        )
        .filter(F.col("sessions") >= min_sessions)
        .withColumn("conversion_rate", F.round(F.col("purchase_sessions") / F.col("sessions"), 6))
        .withColumn("cart_rate", F.round(F.col("cart_sessions") / F.col("sessions"), 6))
        .orderBy(F.desc("sessions"), F.desc("revenue"), F.desc("conversion_rate"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def collect_transitions(transitions: DataFrame, limit: int, min_transition_count: int) -> list[dict[str, Any]]:
    rows = (
        transitions.filter(F.col("transitions") >= min_transition_count)
        .orderBy(F.desc("transitions"), F.desc("revenue"), F.desc("conversion_rate"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def collect_exit_events(session_paths: DataFrame, limit: int) -> list[dict[str, Any]]:
    total_sessions = session_paths.count()
    rows = (
        session_paths.groupBy("last_event")
        .agg(
            F.count("*").alias("sessions"),
            F.sum("has_purchase").alias("purchase_sessions"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.round(F.avg("step_count"), 2).alias("avg_steps"),
        )
        .withColumn("exit_share", F.round(F.col("sessions") / F.lit(total_sessions), 6) if total_sessions else F.lit(0.0))
        .withColumn("purchase_rate", F.round(F.col("purchase_sessions") / F.col("sessions"), 6))
        .orderBy(F.desc("sessions"), F.desc("revenue"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def collect_purchase_paths(session_paths: DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = (
        session_paths.filter(F.col("has_purchase") == 1)
        .groupBy("path_signature")
        .agg(
            F.count("*").alias("purchase_sessions"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.round(F.avg("step_count"), 2).alias("avg_steps"),
            F.round(F.avg("duration_seconds"), 2).alias("avg_duration_seconds"),
        )
        .orderBy(F.desc("purchase_sessions"), F.desc("revenue"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def build_summary(
    session_paths: DataFrame,
    paths: list[dict[str, Any]],
    exits: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    row = session_paths.agg(
        F.count("*").alias("sessions"),
        F.countDistinct("path_signature").alias("unique_paths"),
        F.sum("has_purchase").alias("purchase_sessions"),
        F.sum("has_cart").alias("cart_sessions"),
        F.round(F.sum("revenue"), 2).alias("revenue"),
        F.round(F.avg("step_count"), 2).alias("avg_steps"),
        F.round(F.avg("duration_seconds"), 2).alias("avg_duration_seconds"),
    ).first()
    sessions = int(row["sessions"] or 0)
    purchase_sessions = int(row["purchase_sessions"] or 0)
    cart_sessions = int(row["cart_sessions"] or 0)
    return {
        "contract_version": JOURNEY_CONTRACT_VERSION,
        "run_id": run_id,
        "sessions": sessions,
        "unique_paths": int(row["unique_paths"] or 0),
        "purchase_sessions": purchase_sessions,
        "cart_sessions": cart_sessions,
        "purchase_path_rate": round(purchase_sessions / sessions, 6) if sessions else 0.0,
        "cart_path_rate": round(cart_sessions / sessions, 6) if sessions else 0.0,
        "revenue": float(row["revenue"] or 0),
        "avg_steps": float(row["avg_steps"] or 0),
        "avg_duration_seconds": float(row["avg_duration_seconds"] or 0),
        "top_path": paths[0] if paths else None,
        "top_exit_event": exits[0] if exits else None,
        "top_transition": transitions[0] if transitions else None,
        "recommended_action": "Use high-volume non-purchase paths and remove-from-cart transitions to prioritize UX and merchandising investigations.",
    }


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
