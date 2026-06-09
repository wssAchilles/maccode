from __future__ import annotations

from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


CONVERSION_CONTRACT_VERSION = "analytics-conversion/v1"
MAX_TIME_SERIES_POINTS = 500


def _safe_rate(numerator: float | int | None, denominator: float | int | None) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator or 0) / float(denominator), 6)


def build_session_facts(df: DataFrame) -> DataFrame:
    purchase = F.col("event_type") == "purchase"
    view = F.col("event_type") == "view"
    cart = F.col("event_type") == "cart"

    return (
        df.groupBy("user_session")
        .agg(
            F.min("event_timestamp").alias("session_start"),
            F.max("event_timestamp").alias("session_end"),
            F.min(F.when(view, F.col("event_timestamp"))).alias("first_view_ts"),
            F.min(F.when(cart, F.col("event_timestamp"))).alias("first_cart_ts"),
            F.min(F.when(purchase, F.col("event_timestamp"))).alias("first_purchase_ts"),
            F.max(F.when(view, F.lit(1)).otherwise(F.lit(0))).alias("has_view"),
            F.max(F.when(cart, F.lit(1)).otherwise(F.lit(0))).alias("has_cart"),
            F.max(F.when(purchase, F.lit(1)).otherwise(F.lit(0))).alias("has_purchase"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias(
                "session_revenue"
            ),
            F.countDistinct("product_id").alias("distinct_products"),
            F.to_date(F.min("event_timestamp")).alias("session_date"),
        )
        .withColumn(
            "duration_seconds",
            F.col("session_end").cast("long") - F.col("session_start").cast("long"),
        )
        .withColumn(
            "purchase_latency_minutes",
            F.when(
                F.col("first_view_ts").isNotNull() & F.col("first_purchase_ts").isNotNull(),
                F.round((F.col("first_purchase_ts").cast("long") - F.col("first_view_ts").cast("long")) / 60, 3),
            ),
        )
        .withColumn(
            "ordering_anomaly",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_purchase_ts") < F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_cart_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_purchase_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_purchase_ts") >= F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_cart_purchase_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts"))
                & (F.col("first_purchase_ts") >= F.col("first_cart_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "session_axis_bucket",
            F.concat(
                F.date_format("session_start", "yyyy-MM-dd HH:"),
                F.lpad((F.floor(F.minute("session_start") / 15) * 15).cast("int").cast("string"), 2, "0"),
            ),
        )
    )


def build_conversion_quality(raw_df: DataFrame, session_facts: DataFrame) -> dict[str, Any]:
    session_count = session_facts.count()
    ordering_anomaly_sessions = session_facts.filter(F.col("ordering_anomaly") == 1).count()
    purchase_rows = raw_df.filter(F.col("event_type") == "purchase").count()
    purchase_missing_price_rows = raw_df.filter((F.col("event_type") == "purchase") & F.col("price").isNull()).count()

    return {
        "session_fact_rows": session_count,
        "ordering_anomaly_sessions": ordering_anomaly_sessions,
        "ordering_anomaly_ratio": round(ordering_anomaly_sessions / session_count, 6) if session_count else 0,
        "purchase_missing_price_rows": purchase_missing_price_rows,
        "purchase_missing_price_ratio": round(purchase_missing_price_rows / purchase_rows, 6) if purchase_rows else 0,
    }


def session_funnel(session_facts: DataFrame) -> dict[str, Any]:
    row = session_facts.agg(
        F.count("*").alias("sessions"),
        F.sum("has_view").alias("view_sessions"),
        F.sum("valid_cart_path").alias("cart_sessions"),
        F.sum("valid_cart_purchase_path").alias("purchase_sessions"),
        F.round(F.sum("session_revenue"), 2).alias("revenue"),
        F.round(F.avg(F.when(F.col("purchase_latency_minutes") >= 0, F.col("purchase_latency_minutes"))), 3).alias(
            "avg_purchase_latency_minutes"
        ),
        F.round(F.avg(F.when(F.col("has_purchase") == 1, F.col("session_revenue"))), 2).alias("avg_order_value"),
    ).first()

    sessions = int(row["sessions"] or 0)
    view_sessions = int(row["view_sessions"] or 0)
    cart_sessions = int(row["cart_sessions"] or 0)
    purchase_sessions = int(row["purchase_sessions"] or 0)
    totals = {
        "sessions": sessions,
        "view_sessions": view_sessions,
        "cart_sessions": cart_sessions,
        "purchase_sessions": purchase_sessions,
        "view_to_cart_rate": _safe_rate(cart_sessions, view_sessions),
        "cart_to_purchase_rate": _safe_rate(purchase_sessions, cart_sessions),
        "view_to_purchase_rate": _safe_rate(purchase_sessions, view_sessions),
        "avg_purchase_latency_minutes": float(row["avg_purchase_latency_minutes"] or 0),
        "revenue": float(row["revenue"] or 0),
        "avg_order_value": float(row["avg_order_value"] or 0),
    }
    return {
        "totals": totals,
        "steps": [
            {"step": "view", "sessions": view_sessions, "rate_from_previous": 1.0 if view_sessions else 0.0},
            {"step": "cart", "sessions": cart_sessions, "rate_from_previous": _safe_rate(cart_sessions, view_sessions)},
            {
                "step": "purchase",
                "sessions": purchase_sessions,
                "rate_from_previous": _safe_rate(purchase_sessions, cart_sessions),
            },
        ],
    }


def daily_conversion(session_facts: DataFrame) -> list[dict[str, Any]]:
    axis_column = (
        "session_axis_bucket"
        if session_facts.select("session_date").where(F.col("session_date").isNotNull()).distinct().limit(2).count() == 1
        and "session_axis_bucket" in session_facts.columns
        else "session_date"
    )
    rows = (
        session_facts.groupBy(axis_column)
        .agg(
            F.count("*").alias("sessions"),
            F.sum("valid_purchase_path").alias("purchase_sessions"),
            F.round(F.sum("session_revenue"), 2).alias("revenue"),
        )
        .orderBy(axis_column)
        .limit(MAX_TIME_SERIES_POINTS)
        .collect()
    )
    return [
        {
            "date": row[axis_column].isoformat() if hasattr(row[axis_column], "isoformat") else str(row[axis_column]),
            "sessions": int(row["sessions"] or 0),
            "purchase_sessions": int(row["purchase_sessions"] or 0),
            "view_to_purchase_rate": _safe_rate(row["purchase_sessions"], row["sessions"]),
            "revenue": float(row["revenue"] or 0),
        }
        for row in rows
        if row[axis_column]
    ]


def product_conversion(df: DataFrame, limit: int) -> list[dict[str, Any]]:
    view = F.col("event_type") == "view"
    cart = F.col("event_type") == "cart"
    purchase = F.col("event_type") == "purchase"
    product_sessions = (
        df.groupBy("product_id", "brand", "category_level1", "user_session")
        .agg(
            F.min(F.when(view, F.col("event_timestamp"))).alias("first_view_ts"),
            F.min(F.when(cart, F.col("event_timestamp"))).alias("first_cart_ts"),
            F.min(F.when(purchase, F.col("event_timestamp"))).alias("first_purchase_ts"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias(
                "session_revenue"
            ),
        )
        .withColumn("has_view", F.when(F.col("first_view_ts").isNotNull(), F.lit(1)).otherwise(F.lit(0)))
        .withColumn(
            "valid_cart_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "valid_cart_purchase_path",
            F.when(
                F.col("first_view_ts").isNotNull()
                & F.col("first_cart_ts").isNotNull()
                & F.col("first_purchase_ts").isNotNull()
                & (F.col("first_cart_ts") >= F.col("first_view_ts"))
                & (F.col("first_purchase_ts") >= F.col("first_cart_ts")),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
    )
    rows = (
        product_sessions.groupBy("product_id", "brand", "category_level1")
        .agg(
            F.sum("has_view").alias("views"),
            F.sum("valid_cart_path").alias("carts"),
            F.sum("valid_cart_purchase_path").alias("purchases"),
            F.round(F.sum("session_revenue"), 2).alias("revenue"),
        )
        .orderBy(F.desc("revenue"), F.desc("purchases"), F.desc("views"))
        .limit(limit)
        .collect()
    )
    return [
        {
            "product_id": str(row["product_id"]),
            "brand": row["brand"] or "unknown",
            "category_level1": row["category_level1"] or "unknown",
            "views": int(row["views"] or 0),
            "carts": int(row["carts"] or 0),
            "purchases": int(row["purchases"] or 0),
            "view_to_cart_rate": _safe_rate(row["carts"], row["views"]),
            "cart_to_purchase_rate": _safe_rate(row["purchases"], row["carts"]),
            "revenue": float(row["revenue"] or 0),
        }
        for row in rows
    ]


def build_conversion_metrics(cleaned_df: DataFrame, session_facts: DataFrame, top_n: int) -> dict[str, Any]:
    return {
        "session_funnel": session_funnel(session_facts),
        "conversion_segments": daily_conversion(session_facts),
        "product_conversion": product_conversion(cleaned_df, top_n),
    }
