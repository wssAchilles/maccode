from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import Window
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
    "min_seasonal_points": 3,
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
    incidents = build_incidents(alerts)
    root_cause = build_root_cause(incidents)
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
        "anomaly_incidents": incidents,
        "anomaly_root_cause": root_cause,
        "anomaly_evaluation": build_anomaly_evaluation(scored, incidents, config, run_id),
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
        StructField("incident_id", StringType(), True),
        StructField("baseline_mode", StringType(), True),
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
    signals = signals.withColumn("_dt_order", F.to_date("dt")).withColumn("_weekday", F.dayofweek(F.col("_dt_order")))
    global_history = (
        Window.partitionBy("entity_type", "entity_id", "metric")
        .orderBy("_dt_order", "dt")
        .rowsBetween(Window.unboundedPreceding, -1)
    )
    seasonal_history = (
        Window.partitionBy("entity_type", "entity_id", "metric", "_weekday")
        .orderBy("_dt_order", "dt")
        .rowsBetween(Window.unboundedPreceding, -1)
    )
    with_baseline = (
        signals.withColumn("baseline_median", F.expr("percentile_approx(value, 0.5)").over(global_history))
        .withColumn("baseline_points", F.count("*").over(global_history))
        .withColumn("seasonal_median", F.expr("percentile_approx(value, 0.5)").over(seasonal_history))
        .withColumn("seasonal_points", F.count("*").over(seasonal_history))
        .withColumn(
            "baseline_mode",
            F.when(F.col("seasonal_points") >= int(config["min_seasonal_points"]), F.lit("weekday_median_mad")).otherwise(
                F.lit("global_median_mad")
            ),
        )
        .withColumn(
            "effective_baseline_median",
            F.when(F.col("baseline_mode") == "weekday_median_mad", F.col("seasonal_median")).otherwise(F.col("baseline_median")),
        )
        .withColumn(
            "effective_baseline_points",
            F.when(F.col("baseline_mode") == "weekday_median_mad", F.col("seasonal_points")).otherwise(F.col("baseline_points")),
        )
    )
    deviations = (
        with_baseline.withColumn("global_absolute_deviation", F.abs(F.col("value") - F.col("baseline_median")))
        .withColumn("seasonal_absolute_deviation", F.abs(F.col("value") - F.col("seasonal_median")))
        .withColumn("global_mad", F.expr("percentile_approx(global_absolute_deviation, 0.5)").over(global_history))
        .withColumn("seasonal_mad", F.expr("percentile_approx(seasonal_absolute_deviation, 0.5)").over(seasonal_history))
        .withColumn(
            "effective_baseline_mad",
            F.when(F.col("baseline_mode") == "weekday_median_mad", F.col("seasonal_mad")).otherwise(F.col("global_mad")),
        )
    )
    scored = (
        deviations
        .withColumn("delta", F.round(F.col("value") - F.col("effective_baseline_median"), 6))
        .withColumn("delta_rate", F.round(F.col("delta") / F.when(F.col("effective_baseline_median") == 0, None).otherwise(F.col("effective_baseline_median")), 6))
        .withColumn(
            "robust_z",
            F.round(
                F.abs(F.col("value") - F.col("effective_baseline_median"))
                / F.when(F.col("effective_baseline_mad") == 0, None).otherwise(F.col("effective_baseline_mad") * F.lit(1.4826)),
                6,
            ),
        )
        .withColumn("direction", F.when(F.col("delta") < 0, F.lit("drop")).when(F.col("delta") > 0, F.lit("spike")).otherwise(F.lit("flat")))
        .withColumn(
            "severity",
            F.when(F.col("effective_baseline_points") < int(config["min_baseline_points"]), F.lit("watch"))
            .when(F.col("robust_z") >= float(config["critical_z"]), F.lit("critical"))
            .when(F.col("robust_z") >= float(config["warning_z"]), F.lit("warning"))
            .when((F.col("value") == 0) & (F.col("effective_baseline_median") >= float(config["min_volume"])), F.lit("critical"))
            .otherwise(F.lit("normal")),
        )
        .withColumn("is_anomaly", F.col("severity").isin("critical", "warning"))
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(ANOMALY_CONTRACT_VERSION))
        .withColumn("incident_id", F.concat_ws(":", F.lit("incident"), F.col("dt"), F.col("entity_type"), F.col("entity_id"), F.col("metric")))
    )
    return scored.select(
        "dt",
        "entity_type",
        "entity_id",
        "entity_label",
        "metric",
        "value",
        F.col("effective_baseline_median").alias("baseline_median"),
        F.col("effective_baseline_mad").alias("baseline_mad"),
        F.col("effective_baseline_points").alias("baseline_points"),
        "delta",
        "delta_rate",
        "robust_z",
        "direction",
        "severity",
        "is_anomaly",
        "source_run_id",
        "contract_version",
        "incident_id",
        "baseline_mode",
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
        "baseline": "trailing weekday seasonal median + MAD when enough same-weekday points exist, otherwise trailing global median + MAD",
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
                "name": "weekday_seasonal_baseline",
                "description": "same weekday baseline is used when seasonal points reach threshold",
                "threshold": int(config["min_seasonal_points"]),
            },
            {
                "name": "zero_after_volume",
                "description": "metric collapses to zero after a non-trivial baseline",
                "threshold": float(config["min_volume"]),
            },
        ],
    }


def build_incidents(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    incidents: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        incident_id = alert.get("incident_id") or f"incident:{alert.get('dt')}:{alert.get('entity_type')}:{alert.get('entity_id')}:{alert.get('metric')}"
        incident = incidents.setdefault(
            incident_id,
            {
                "contract_version": ANOMALY_CONTRACT_VERSION,
                "incident_id": incident_id,
                "run_id": alert["run_id"],
                "dt": alert["dt"],
                "severity": alert["severity"],
                "entity_type": alert["entity_type"],
                "entity_id": alert["entity_id"],
                "entity_label": alert["entity_label"],
                "metric": alert["metric"],
                "alert_count": 0,
                "max_robust_z": 0.0,
                "impact_value": 0.0,
                "root_cause_contributions": [],
                "recommended_action": alert["recommended_action"],
            },
        )
        incident["alert_count"] += 1
        incident["severity"] = _higher_severity(incident["severity"], alert["severity"])
        incident["max_robust_z"] = max(float(incident["max_robust_z"] or 0), float(alert.get("robust_z") or 0))
        impact = abs(float(alert.get("delta") or 0))
        incident["impact_value"] = round(float(incident["impact_value"] or 0) + impact, 6)
        incident["root_cause_contributions"].append(
            {
                "dimension": alert["entity_type"],
                "value": alert["entity_label"],
                "metric": alert["metric"],
                "contribution": round(impact, 6),
                "direction": alert["direction"],
            }
        )
    for incident in incidents.values():
        total = float(incident["impact_value"] or 0)
        for contribution in incident["root_cause_contributions"]:
            contribution["contribution_share"] = round(float(contribution["contribution"]) / total, 6) if total else 0.0
    return sorted(incidents.values(), key=lambda row: _incident_sort_key(row))


def build_root_cause(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for incident in incidents:
        for contribution in incident.get("root_cause_contributions", []):
            rows.append(
                {
                    "contract_version": ANOMALY_CONTRACT_VERSION,
                    "incident_id": incident["incident_id"],
                    "dt": incident["dt"],
                    "severity": incident["severity"],
                    "dimension": contribution["dimension"],
                    "value": contribution["value"],
                    "metric": contribution["metric"],
                    "contribution": contribution["contribution"],
                    "contribution_share": contribution["contribution_share"],
                    "direction": contribution["direction"],
                }
            )
    return sorted(rows, key=lambda row: (-float(row["contribution"]), row["incident_id"]))


def build_anomaly_evaluation(scored: DataFrame, incidents: list[dict[str, Any]], config: dict[str, Any], run_id: str) -> dict[str, Any]:
    row = scored.agg(
        F.count("*").alias("signal_count"),
        F.sum(F.when(F.col("baseline_mode") == "weekday_median_mad", 1).otherwise(0)).alias("seasonal_signal_count"),
        F.sum(F.when(F.col("is_anomaly"), 1).otherwise(0)).alias("anomaly_signal_count"),
        F.countDistinct("dt").alias("monitored_days"),
    ).first()
    signal_count = int(row["signal_count"] or 0)
    seasonal_signal_count = int(row["seasonal_signal_count"] or 0)
    anomaly_signal_count = int(row["anomaly_signal_count"] or 0)
    return {
        "contract_version": ANOMALY_CONTRACT_VERSION,
        "run_id": run_id,
        "baseline": {
            "seasonal_signal_count": seasonal_signal_count,
            "seasonal_coverage_rate": round(seasonal_signal_count / signal_count, 6) if signal_count else 0.0,
            "min_seasonal_points": int(config["min_seasonal_points"]),
            "min_baseline_points": int(config["min_baseline_points"]),
        },
        "incidents": {
            "incident_count": len(incidents),
            "critical_incidents": sum(1 for row in incidents if row["severity"] == "critical"),
            "warning_incidents": sum(1 for row in incidents if row["severity"] == "warning"),
        },
        "alert_budget": {
            "anomaly_signal_count": anomaly_signal_count,
            "signal_count": signal_count,
            "anomaly_rate": round(anomaly_signal_count / signal_count, 6) if signal_count else 0.0,
            "max_alerts": int(config["max_alerts"]),
        },
        "quality_gates": [
            {
                "name": "baseline_points_available",
                "actual": int(row["monitored_days"] or 0),
                "operator": ">=",
                "expected": int(config["min_baseline_points"]),
                "passed": int(row["monitored_days"] or 0) >= int(config["min_baseline_points"]),
            },
            {
                "name": "incident_budget",
                "actual": len(incidents),
                "operator": "<=",
                "expected": int(config["max_alerts"]),
                "passed": len(incidents) <= int(config["max_alerts"]),
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
        "incident_id": row.get("incident_id"),
        "baseline_mode": row.get("baseline_mode") or "global_median_mad",
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
        "incident_id": f"incident:control:{code}",
        "baseline_mode": "control_gate",
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


def _higher_severity(left: str, right: str) -> str:
    rank = {"critical": 0, "warning": 1, "watch": 2, "normal": 3}
    return left if rank.get(left, 4) <= rank.get(right, 4) else right


def _incident_sort_key(incident: dict[str, Any]) -> tuple[int, float]:
    severity_rank = {"critical": 0, "warning": 1, "watch": 2}.get(incident["severity"], 3)
    return (severity_rank, -float(incident.get("impact_value") or 0))
