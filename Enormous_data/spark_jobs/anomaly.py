from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType


ANOMALY_CONTRACT_VERSION = "ops-anomaly-radar/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "max_alerts": 100,
    "max_product_entities": 500,
    "min_baseline_points": 3,
    "warning_z": 3.5,
    "critical_z": 6.0,
    "min_volume": 20,
}


def anomaly_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_anomaly_outputs(
    daily_category: DataFrame,
    daily_product: DataFrame,
    feature_mart_quality: dict[str, Any],
    feature_mart_freshness: dict[str, Any],
    config: dict[str, Any],
    *,
    run_id: str,
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    signals = build_daily_signals(daily_category, daily_product, int(config["max_product_entities"])).persist(StorageLevel.MEMORY_AND_DISK)
    scored = score_daily_signals(signals, config, run_id).persist(StorageLevel.MEMORY_AND_DISK)
    alerts = build_alert_preview(scored, int(config["max_alerts"]))
    timeline = build_timeline(scored, int(config["preview_limit"]))
    rules = build_rules_report(config)
    summary = build_anomaly_summary(run_id, scored, alerts, feature_mart_quality, feature_mart_freshness)
    quality_alerts = build_quality_alerts(run_id, feature_mart_quality, feature_mart_freshness)
    all_alerts = sorted([*quality_alerts, *alerts], key=lambda item: _alert_sort_key(item))[: int(config["max_alerts"])]
    summary["alert_count"] = len(all_alerts)
    summary["critical_count"] = sum(1 for alert in all_alerts if alert["severity"] == "critical")
    summary["warning_count"] = sum(1 for alert in all_alerts if alert["severity"] == "warning")
    summary["watch_count"] = int(summary["watch_signal_count"]) + sum(1 for alert in all_alerts if alert["severity"] == "watch")
    if summary["critical_count"]:
        summary["radar_status"] = "critical"
    elif summary["warning_count"]:
        summary["radar_status"] = "warning"
    elif summary["monitored_days"] < int(config["min_baseline_points"]):
        summary["radar_status"] = "insufficient_baseline"
    else:
        summary["radar_status"] = "healthy"

    frames = {
        "daily_signals": scored,
        "alert_evidence": daily_category.sparkSession.createDataFrame(
            [_alert_row(alert) for alert in all_alerts] or [_empty_alert_row(run_id)],
            schema=ALERT_SCHEMA,
        ),
    }
    metrics = {
        "anomaly_summary": summary,
        "anomaly_alerts": all_alerts,
        "anomaly_timeline": timeline,
        "anomaly_rules": rules,
    }
    signals.unpersist()
    return frames, metrics


ALERT_SCHEMA = StructType(
    [
        StructField("contract_version", StringType(), False),
        StructField("run_id", StringType(), False),
        StructField("dt", StringType(), True),
        StructField("severity", StringType(), False),
        StructField("alert_code", StringType(), False),
        StructField("entity_type", StringType(), False),
        StructField("entity_id", StringType(), False),
        StructField("entity_label", StringType(), False),
        StructField("metric", StringType(), False),
        StructField("actual", DoubleType(), True),
        StructField("baseline", DoubleType(), True),
        StructField("delta", DoubleType(), True),
        StructField("delta_rate", DoubleType(), True),
        StructField("robust_z", DoubleType(), True),
        StructField("direction", StringType(), False),
        StructField("message", StringType(), False),
        StructField("recommended_action", StringType(), False),
    ]
)


def build_daily_signals(daily_category: DataFrame, daily_product: DataFrame, max_product_entities: int) -> DataFrame:
    category_signals = _signalize(
        daily_category,
        entity_type="category",
        entity_id_col="category_level1",
        entity_label_col="category_level1",
        metrics=["views", "purchases", "revenue", "conversion_rate"],
    )
    if max_product_entities <= 0:
        return category_signals

    top_products = (
        daily_product.groupBy("product_id")
        .agg(
            F.sum(F.coalesce(F.col("views"), F.lit(0))).alias("total_views"),
            F.sum(F.coalesce(F.col("purchases"), F.lit(0))).alias("total_purchases"),
            F.sum(F.coalesce(F.col("revenue"), F.lit(0.0))).alias("total_revenue"),
        )
        .orderBy(F.desc("total_revenue"), F.desc("total_purchases"), F.desc("total_views"))
        .limit(max_product_entities)
        .select("product_id")
    )
    product_base = (
        daily_product.join(top_products, on="product_id", how="inner")
        .withColumn("entity_label", F.concat_ws(" / ", F.col("brand"), F.col("category_level1")))
    )
    product_signals = _signalize(
        product_base,
        entity_type="product",
        entity_id_col="product_id",
        entity_label_col="entity_label",
        metrics=["views", "purchases", "revenue", "view_to_purchase_rate"],
    )
    return category_signals.unionByName(product_signals)


def score_daily_signals(signals: DataFrame, config: dict[str, Any], run_id: str) -> DataFrame:
    baseline = signals.groupBy("entity_type", "entity_id", "metric").agg(
        F.expr("percentile_approx(value, 0.5)").alias("baseline_median"),
        F.count("*").alias("baseline_points"),
    )
    with_baseline = signals.join(baseline, on=["entity_type", "entity_id", "metric"], how="left")
    deviations = with_baseline.withColumn("absolute_deviation", F.abs(F.col("value") - F.col("baseline_median")))
    mad = deviations.groupBy("entity_type", "entity_id", "metric").agg(
        F.expr("percentile_approx(absolute_deviation, 0.5)").alias("baseline_mad")
    )
    scored = (
        deviations.join(mad, on=["entity_type", "entity_id", "metric"], how="left")
        .withColumn("delta", F.round(F.col("value") - F.col("baseline_median"), 6))
        .withColumn("delta_rate", F.round(F.col("delta") / F.when(F.col("baseline_median") == 0, None).otherwise(F.col("baseline_median")), 6))
        .withColumn(
            "robust_z",
            F.round(
                F.abs(F.col("value") - F.col("baseline_median"))
                / F.when(F.col("baseline_mad") == 0, None).otherwise(F.col("baseline_mad") * F.lit(1.4826)),
                6,
            ),
        )
        .withColumn("direction", F.when(F.col("delta") < 0, F.lit("drop")).when(F.col("delta") > 0, F.lit("spike")).otherwise(F.lit("flat")))
        .withColumn(
            "severity",
            F.when(F.col("baseline_points") < int(config["min_baseline_points"]), F.lit("watch"))
            .when(F.col("robust_z") >= float(config["critical_z"]), F.lit("critical"))
            .when(F.col("robust_z") >= float(config["warning_z"]), F.lit("warning"))
            .when((F.col("value") == 0) & (F.col("baseline_median") >= float(config["min_volume"])), F.lit("critical"))
            .otherwise(F.lit("normal")),
        )
        .withColumn("is_anomaly", F.col("severity").isin("critical", "warning"))
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(ANOMALY_CONTRACT_VERSION))
    )
    return scored.select(
        "dt",
        "entity_type",
        "entity_id",
        "entity_label",
        "metric",
        "value",
        "baseline_median",
        "baseline_mad",
        "baseline_points",
        "delta",
        "delta_rate",
        "robust_z",
        "direction",
        "severity",
        "is_anomaly",
        "source_run_id",
        "contract_version",
    )


def build_alert_preview(scored: DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = (
        scored.filter(F.col("severity").isin("critical", "warning"))
        .orderBy(F.desc("robust_z"), F.desc("value"), F.asc("entity_type"), F.asc("entity_id"), F.asc("metric"))
        .limit(limit)
        .collect()
    )
    return [_alert_from_row(row.asDict()) for row in rows]


def build_timeline(scored: DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = (
        scored.groupBy("dt")
        .agg(
            F.count("*").alias("signal_count"),
            F.sum(F.when(F.col("severity") == "critical", 1).otherwise(0)).alias("critical_count"),
            F.sum(F.when(F.col("severity") == "warning", 1).otherwise(0)).alias("warning_count"),
            F.sum(F.when(F.col("severity") == "watch", 1).otherwise(0)).alias("watch_count"),
            F.round(F.max(F.coalesce(F.col("robust_z"), F.lit(0))), 6).alias("max_robust_z"),
        )
        .orderBy(F.desc("dt"))
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def build_anomaly_summary(
    run_id: str,
    scored: DataFrame,
    alerts: list[dict[str, Any]],
    feature_mart_quality: dict[str, Any],
    feature_mart_freshness: dict[str, Any],
) -> dict[str, Any]:
    row = scored.agg(
        F.count("*").alias("signal_count"),
        F.countDistinct("entity_id").alias("monitored_entities"),
        F.countDistinct("dt").alias("monitored_days"),
        F.sum(F.when(F.col("severity") == "critical", 1).otherwise(0)).alias("critical_signal_count"),
        F.sum(F.when(F.col("severity") == "warning", 1).otherwise(0)).alias("warning_signal_count"),
        F.sum(F.when(F.col("severity") == "watch", 1).otherwise(0)).alias("watch_signal_count"),
        F.round(F.max(F.coalesce(F.col("robust_z"), F.lit(0))), 6).alias("max_robust_z"),
        F.min("dt").alias("min_dt"),
        F.max("dt").alias("max_dt"),
    ).first()
    top_alert = alerts[0] if alerts else None
    return {
        "contract_version": ANOMALY_CONTRACT_VERSION,
        "run_id": run_id,
        "radar_status": "healthy",
        "signal_count": int(row["signal_count"] or 0),
        "monitored_entities": int(row["monitored_entities"] or 0),
        "monitored_days": int(row["monitored_days"] or 0),
        "critical_signal_count": int(row["critical_signal_count"] or 0),
        "warning_signal_count": int(row["warning_signal_count"] or 0),
        "watch_signal_count": int(row["watch_signal_count"] or 0),
        "max_robust_z": float(row["max_robust_z"] or 0),
        "date_range": {"min_dt": row["min_dt"], "max_dt": row["max_dt"]},
        "feature_mart_quality_status": feature_mart_quality.get("quality_status"),
        "feature_mart_freshness_status": feature_mart_freshness.get("sla_status"),
        "top_alert": top_alert,
    }


def build_quality_alerts(
    run_id: str,
    feature_mart_quality: dict[str, Any],
    feature_mart_freshness: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    if feature_mart_quality.get("quality_status") != "passed":
        alerts.append(
            _control_alert(
                run_id,
                "critical",
                "feature_mart_quality_failed",
                "Feature Mart quality gate failed",
                "Inspect quarantined rows and duplicate event keys before using downstream recommendations.",
            )
        )
    if feature_mart_freshness.get("sla_status") == "stale":
        alerts.append(
            _control_alert(
                run_id,
                "warning",
                "feature_mart_freshness_stale",
                "Feature Mart freshness SLA is stale",
                "Refresh HDFS ingestion or widen the accepted freshness window for historical demos.",
            )
        )
    return alerts


def build_rules_report(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": ANOMALY_CONTRACT_VERSION,
        "baseline": "median + median absolute deviation across current feature mart window",
        "rules": [
            {
                "name": "critical_robust_z",
                "description": "absolute robust z-score exceeds critical threshold",
                "threshold": float(config["critical_z"]),
            },
            {
                "name": "warning_robust_z",
                "description": "absolute robust z-score exceeds warning threshold",
                "threshold": float(config["warning_z"]),
            },
            {
                "name": "insufficient_baseline",
                "description": "entity has too few points to alert safely and is placed on watch",
                "threshold": int(config["min_baseline_points"]),
            },
            {
                "name": "zero_after_volume",
                "description": "metric collapses to zero after a non-trivial baseline",
                "threshold": float(config["min_volume"]),
            },
        ],
    }


def _signalize(
    frame: DataFrame,
    *,
    entity_type: str,
    entity_id_col: str,
    entity_label_col: str,
    metrics: list[str],
) -> DataFrame:
    pieces = []
    for metric in metrics:
        pieces.append(
            frame.select(
                F.col("dt").cast("string").alias("dt"),
                F.lit(entity_type).alias("entity_type"),
                F.col(entity_id_col).cast("string").alias("entity_id"),
                F.coalesce(F.col(entity_label_col).cast("string"), F.lit("unknown")).alias("entity_label"),
                F.lit(metric).alias("metric"),
                F.coalesce(F.col(metric).cast("double"), F.lit(0.0)).alias("value"),
            )
        )
    result = pieces[0]
    for piece in pieces[1:]:
        result = result.unionByName(piece)
    return result.filter(F.col("entity_id").isNotNull() & F.col("dt").isNotNull())


def _alert_from_row(row: dict[str, Any]) -> dict[str, Any]:
    severity = row["severity"]
    metric = row["metric"]
    direction = row["direction"]
    entity_type = row["entity_type"]
    return {
        "contract_version": ANOMALY_CONTRACT_VERSION,
        "run_id": row["source_run_id"],
        "dt": row["dt"],
        "severity": severity,
        "alert_code": f"{entity_type}_{metric}_{direction}",
        "entity_type": entity_type,
        "entity_id": row["entity_id"],
        "entity_label": row["entity_label"],
        "metric": metric,
        "actual": row["value"],
        "baseline": row["baseline_median"],
        "delta": row["delta"],
        "delta_rate": row["delta_rate"],
        "robust_z": row["robust_z"],
        "direction": direction,
        "message": f"{entity_type} {row['entity_label']} {metric} {direction} detected on {row['dt']}",
        "recommended_action": _recommended_action(metric, direction, severity),
    }


def _control_alert(run_id: str, severity: str, code: str, message: str, action: str) -> dict[str, Any]:
    return {
        "contract_version": ANOMALY_CONTRACT_VERSION,
        "run_id": run_id,
        "dt": None,
        "severity": severity,
        "alert_code": code,
        "entity_type": "control",
        "entity_id": code,
        "entity_label": "pipeline control",
        "metric": "quality",
        "actual": None,
        "baseline": None,
        "delta": None,
        "delta_rate": None,
        "robust_z": None,
        "direction": "control",
        "message": message,
        "recommended_action": action,
    }


def _recommended_action(metric: str, direction: str, severity: str) -> str:
    if direction == "drop" and metric in {"purchases", "revenue", "conversion_rate", "view_to_purchase_rate"}:
        return "Check checkout funnel, recommendation fallback, and stock or price changes for this entity."
    if direction == "spike" and metric in {"views", "purchases", "revenue"}:
        return "Inspect campaign, bot traffic, price promotion, and downstream capacity before scaling exposure."
    if severity == "critical":
        return "Open an incident review and compare against raw events plus Feature Mart partitions."
    return "Monitor the next refresh and verify whether the movement is business-driven."


def _alert_sort_key(alert: dict[str, Any]) -> tuple[int, float]:
    severity_rank = {"critical": 0, "warning": 1, "watch": 2}.get(alert["severity"], 3)
    robust_z = alert.get("robust_z") or 0
    return (severity_rank, -float(robust_z))


def _alert_row(alert: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in alert.items()}


def _empty_alert_row(run_id: str) -> dict[str, Any]:
    return _alert_row(_control_alert(run_id, "watch", "no_alerts", "No anomaly alerts generated", "No action required."))


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


def _json_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value
