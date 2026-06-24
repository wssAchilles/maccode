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

    # 1. 对事件流进行初步字段合法性过滤
    base_filtered = (
        normalized.filter(F.col("event_type").isin(EVENT_TYPES))
        .filter(F.col("event_timestamp").isNotNull())
        .filter(F.col("product_id").isNotNull())
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("price").isNull() | ((F.col("price") >= 0) & (F.col("price") <= 100000)))
        .dropDuplicates(["event_time", "event_type", "product_id", "user_id", "user_session"])
    )

    # 如果数据集为空，不执行聚类风控以防报错
    if base_filtered.rdd.isEmpty():
        return base_filtered

    # 2. 分组计算 session 特征指标（事件总数、会话时长、事件频率密度、购买总数）
    session_stats = (
        base_filtered.groupBy("user_session")
        .agg(
            F.count(F.lit(1)).alias("session_events"),
            (F.max(F.col("event_timestamp")).cast("long") - F.min(F.col("event_timestamp")).cast("long")).alias("session_duration"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("session_purchases")
        )
        .withColumn("session_duration", F.when(F.col("session_duration") <= 0, 1).otherwise(F.col("session_duration")))
        .withColumn("session_density", F.col("session_events") / F.col("session_duration"))
    )

    # 3. 统计全局分布并计算 3 倍标准差阈值，包含硬性底线防御限制
    stats_row = session_stats.agg(
        F.avg("session_density").alias("avg_density"),
        F.stddev("session_density").alias("std_density"),
        F.avg("session_purchases").alias("avg_purchases"),
        F.stddev("session_purchases").alias("std_purchases")
    ).first()

    avg_density = float(stats_row["avg_density"] or 0.0)
    std_density = float(stats_row["std_density"] or 1.0)
    avg_purchases = float(stats_row["avg_purchases"] or 0.0)
    std_purchases = float(stats_row["std_purchases"] or 1.0)

    # 爬虫密度门槛：自适应 std，并将其限制在 [2.0, 10.0] 的安全范围内，防止大异常点反向膨胀标准差
    density_limit = min(10.0, max(2.0, avg_density + 3 * std_density))
    # 异常刷单购买门槛：自适应 std，并限制在 [5.0, 15.0] 的安全笔数范围内
    purchase_limit = min(15.0, max(5.0, avg_purchases + 3 * std_purchases))

    # 4. 提取恶意黑名单 Session
    malicious_sessions = session_stats.filter(
        (F.col("session_density") > density_limit) |
        (F.col("session_purchases") > purchase_limit)
    ).select("user_session")

    # 5. 使用 anti-join 将恶意流量从主事件流中剔除，保护下游计算
    cleaned = base_filtered.join(malicious_sessions, on="user_session", how="left_anti")
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

    # 估算被风控系统拦截剔除的行数
    # 在字段合法性清洗后的基础事件流上，由于 session 异常而被过滤的事件行数
    raw_normalized = (
        raw_df.filter(F.col("event_type").isin(EVENT_TYPES))
        .filter(F.col("product_id").isNotNull())
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("price").isNull() | ((F.col("price") >= 0) & (F.col("price") <= 100000)))
        .dropDuplicates(["event_time", "event_type", "product_id", "user_id", "user_session"])
    )
    bot_filtered_count = max(0, raw_normalized.count() - cleaned_count)

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
        "bot_filtered_rows": bot_filtered_count,
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
