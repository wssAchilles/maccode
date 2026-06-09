from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


MAX_TIME_SERIES_POINTS = 500


def _uses_hourly_axis(df: DataFrame) -> bool:
    return df.select("event_date").where(F.col("event_date").isNotNull()).distinct().limit(2).count() == 1


def _has_column(df: DataFrame, column: str) -> bool:
    return column in df.columns


def _intraday_bucket(df: DataFrame):
    if not _has_column(df, "event_timestamp"):
        return None
    ten_minute = F.lpad((F.floor(F.minute("event_timestamp") / 10) * 10).cast("int").cast("string"), 2, "0")
    return F.concat(F.date_format("event_timestamp", "yyyy-MM-dd HH:"), ten_minute)


def _hour_label(date_value: object, hour_value: object) -> str:
    hour = int(hour_value or 0)
    return f"{date_value.isoformat()} {hour:02d}:00"


def event_type_count(df: DataFrame) -> list[dict[str, object]]:
    rows = df.groupBy("event_type").count().orderBy(F.desc("count")).collect()
    return [{"name": row["event_type"], "value": int(row["count"])} for row in rows]


def daily_events(df: DataFrame) -> list[dict[str, object]]:
    if _uses_hourly_axis(df):
        bucket = _intraday_bucket(df)
        if bucket is not None:
            rows = df.withColumn("axis_bucket", bucket).groupBy("axis_bucket").count().orderBy("axis_bucket").limit(MAX_TIME_SERIES_POINTS).collect()
            return [{"date": row["axis_bucket"], "value": int(row["count"])} for row in rows if row["axis_bucket"]]

        rows = df.groupBy("event_date", "event_hour").count().orderBy("event_date", "event_hour").limit(MAX_TIME_SERIES_POINTS).collect()
        return [
            {"date": _hour_label(row["event_date"], row["event_hour"]), "value": int(row["count"])}
            for row in rows
            if row["event_date"] is not None and row["event_hour"] is not None
        ]

    rows = df.groupBy("event_date").count().orderBy("event_date").limit(MAX_TIME_SERIES_POINTS).collect()
    return [{"date": row["event_date"].isoformat(), "value": int(row["count"])} for row in rows if row["event_date"]]


def daily_sales(df: DataFrame) -> list[dict[str, object]]:
    purchase = df.filter(F.col("event_type") == "purchase")
    if _uses_hourly_axis(purchase):
        bucket = _intraday_bucket(purchase)
        if bucket is not None:
            rows = (
                purchase.withColumn("axis_bucket", bucket)
                .groupBy("axis_bucket")
                .agg(F.round(F.sum("price"), 2).alias("sales"))
                .orderBy("axis_bucket")
                .limit(MAX_TIME_SERIES_POINTS)
                .collect()
            )
            return [{"date": row["axis_bucket"], "value": float(row["sales"] or 0)} for row in rows if row["axis_bucket"]]

        rows = (
            purchase.groupBy("event_date", "event_hour")
            .agg(F.round(F.sum("price"), 2).alias("sales"))
            .orderBy("event_date", "event_hour")
            .limit(MAX_TIME_SERIES_POINTS)
            .collect()
        )
        return [
            {"date": _hour_label(row["event_date"], row["event_hour"]), "value": float(row["sales"] or 0)}
            for row in rows
            if row["event_date"] is not None and row["event_hour"] is not None
        ]

    rows = (
        purchase
        .groupBy("event_date")
        .agg(F.round(F.sum("price"), 2).alias("sales"))
        .orderBy("event_date")
        .limit(MAX_TIME_SERIES_POINTS)
        .collect()
    )
    return [{"date": row["event_date"].isoformat(), "value": float(row["sales"] or 0)} for row in rows if row["event_date"]]


def top_categories(df: DataFrame, limit: int) -> list[dict[str, object]]:
    rows = (
        df.groupBy("category_level1")
        .count()
        .orderBy(F.desc("count"))
        .limit(limit)
        .collect()
    )
    return [{"name": row["category_level1"] or "unknown", "value": int(row["count"])} for row in rows]


def top_brands(df: DataFrame, limit: int) -> list[dict[str, object]]:
    rows = (
        df.filter(F.col("event_type") == "purchase")
        .groupBy("brand")
        .agg(F.count("*").alias("orders"), F.round(F.sum("price"), 2).alias("sales"))
        .orderBy(F.desc("sales"))
        .limit(limit)
        .collect()
    )
    return [
        {"name": row["brand"] or "unknown", "orders": int(row["orders"]), "value": float(row["sales"] or 0)}
        for row in rows
    ]


def dashboard_summary(df: DataFrame, quality: dict[str, int]) -> dict[str, object]:
    purchase = df.filter(F.col("event_type") == "purchase")
    sales = purchase.agg(F.round(F.sum("price"), 2).alias("sales")).first()["sales"] or 0
    users = df.select("user_id").distinct().count()
    sessions = df.select("user_session").distinct().count()

    return {
        **quality,
        "unique_users": users,
        "unique_sessions": sessions,
        "total_sales": float(sales),
    }


def build_metrics(df: DataFrame, quality: dict[str, int], top_n: int) -> dict[str, object]:
    return {
        "summary": dashboard_summary(df, quality),
        "event_type_count": event_type_count(df),
        "daily_events": daily_events(df),
        "daily_sales": daily_sales(df),
        "top_categories": top_categories(df, top_n),
        "top_brands": top_brands(df, top_n),
    }
