from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark import StorageLevel


FORECAST_CONTRACT_VERSION = "demand-forecasting/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "forecast_horizon_days": 7,
    "training_window_days": 28,
    "backtest_window_days": 7,
    "backtest_windows": [1, 3, 7],
    "preview_limit": 100,
    "top_entities": 12,
    "min_history_days": 7,
    "max_site_wape": 0.35,
    "min_trailing_day_actual_ratio": 0.5,
    "high_risk_drop_rate": -0.15,
    "medium_risk_drop_rate": -0.08,
    "history_collect_days": 90,
    "max_driver_history_rows": 2000,
}


def forecasting_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_forecasting_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    daily = build_daily_demand(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    history_days = _bounded_history_days(config)
    max_driver_history_rows = int(config["max_driver_history_rows"])
    selected_daily = select_forecast_daily_rows(
        daily,
        int(config["top_entities"]),
        history_days,
    ).limit(max_driver_history_rows)
    daily_rows = [
        _json_safe(row.asDict())
        for row in selected_daily.collect()
    ]
    driver_history = {
        "requested_history_days": int(config["history_collect_days"]),
        "collected_history_days": history_days,
        "max_driver_history_rows": max_driver_history_rows,
        "driver_history_rows": len(daily_rows),
    }
    complete_daily_rows, excluded_dates = exclude_incomplete_trailing_dates(daily_rows, config)
    forecast_rows = build_forecast_rows(complete_daily_rows, config)
    entity_rows = build_entity_rows(complete_daily_rows, forecast_rows, config)
    backtest_rows = build_backtest_rows(complete_daily_rows, config)
    evaluation = build_backtest_evaluation(backtest_rows, config, run_id)
    quality = build_quality(complete_daily_rows, backtest_rows, config, excluded_dates, driver_history)
    risks = build_risks(entity_rows, config)
    summary = build_summary(complete_daily_rows, forecast_rows, entity_rows, risks, quality, config, run_id, input_snapshot, driver_history)

    spark = cleaned_df.sparkSession
    forecast_frame = spark.createDataFrame(forecast_rows) if forecast_rows else spark.createDataFrame([], daily.schema)
    entity_frame = spark.createDataFrame(entity_rows) if entity_rows else spark.createDataFrame([], daily.schema)
    frames = {
        "daily_demand": daily,
        "forecast_series": forecast_frame,
        "forecast_entities": entity_frame,
    }
    metrics = {
        "forecasting_summary": summary,
        "forecasting_series": forecast_rows[: int(config["preview_limit"])],
        "forecasting_entities": entity_rows[: int(config["preview_limit"])],
        "forecasting_backtest": backtest_rows[: int(config["preview_limit"])],
        "forecasting_evaluation": evaluation,
        "forecasting_risks": risks[: int(config["preview_limit"])],
        "forecasting_quality": quality,
    }
    return frames, metrics


def build_daily_demand(cleaned_df: DataFrame) -> DataFrame:
    purchase = F.col("event_type") == "purchase"
    base = cleaned_df.withColumn("dt", F.to_date("event_timestamp"))
    site = (
        base.groupBy("dt")
        .agg(
            F.countDistinct("user_session").alias("session_count"),
            F.countDistinct(F.when(purchase, F.col("user_id"))).alias("buyer_count"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("site"))
        .withColumn("entity_key", F.lit("all"))
        .withColumn("entity_label", F.lit("全站"))
    )
    category = (
        base.groupBy("dt", "category_level1")
        .agg(
            F.countDistinct("user_session").alias("session_count"),
            F.countDistinct(F.when(purchase, F.col("user_id"))).alias("buyer_count"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("category"))
        .withColumnRenamed("category_level1", "entity_key")
        .withColumn("entity_label", F.col("entity_key"))
    )
    return (
        site.unionByName(category)
        .withColumn("avg_order_value", F.round(F.col("gmv") / F.when(F.col("purchase_count") == 0, None).otherwise(F.col("purchase_count")), 2))
        .withColumn("view_to_purchase_rate", F.round(F.col("purchase_count") / F.when(F.col("views") == 0, None).otherwise(F.col("views")), 6))
        .withColumn("dt", F.date_format("dt", "yyyy-MM-dd"))
        .select(
            "dt",
            "scope",
            "entity_key",
            "entity_label",
            "session_count",
            "buyer_count",
            "purchase_count",
            "gmv",
            "avg_order_value",
            "view_to_purchase_rate",
        )
    )


def select_forecast_daily_rows(daily: DataFrame, top_entities: int, history_days: int | None = None) -> DataFrame:
    bounded_daily = daily
    if history_days and history_days > 0:
        latest = daily.agg(F.max(F.to_date("dt")).alias("latest_dt"))
        bounded_daily = (
            daily.crossJoin(latest)
            .where(F.col("latest_dt").isNull() | (F.to_date("dt") >= F.date_sub(F.col("latest_dt"), history_days - 1)))
            .drop("latest_dt")
        )
    site_rows = bounded_daily.filter(F.col("scope") == "site")
    top_categories = (
        bounded_daily.filter(F.col("scope") == "category")
        .groupBy("entity_key")
        .agg(F.sum("gmv").alias("entity_gmv"))
        .orderBy(F.desc("entity_gmv"), "entity_key")
        .limit(top_entities)
        .select("entity_key")
    )
    category_rows = bounded_daily.filter(F.col("scope") == "category").join(top_categories, "entity_key", "inner")
    return site_rows.unionByName(category_rows).orderBy("scope", "entity_key", "dt")


def _bounded_history_days(config: dict[str, Any]) -> int:
    requested_days = max(1, int(config["history_collect_days"]))
    entity_slots = max(1, int(config["top_entities"]) + 1)
    max_rows = max(1, int(config["max_driver_history_rows"]))
    max_days_by_rows = max(1, max_rows // entity_slots)
    return min(requested_days, max_days_by_rows)


def exclude_incomplete_trailing_dates(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    site_rows = sorted([row for row in daily_rows if row["scope"] == "site"], key=lambda row: row["dt"])
    if len(site_rows) < 3:
        return daily_rows, []

    latest = site_rows[-1]
    comparison_window = site_rows[-min(8, len(site_rows)) : -1]
    baseline = _median([float(row.get("gmv") or 0) for row in comparison_window])
    latest_gmv = float(latest.get("gmv") or 0)
    threshold = float(config["min_trailing_day_actual_ratio"])
    if baseline <= 0 or latest_gmv >= baseline * threshold:
        return daily_rows, []

    excluded = latest["dt"]
    return [row for row in daily_rows if row["dt"] != excluded], [excluded]


def build_forecast_rows(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(config["forecast_horizon_days"])
    entities = select_entities(daily_rows, int(config["top_entities"]))
    results: list[dict[str, Any]] = []
    for key, rows in entities.items():
        ordered = sorted(rows, key=lambda row: row["dt"])
        max_dt = _parse_date(ordered[-1]["dt"])
        history_days = len({row["dt"] for row in ordered})
        recent = ordered[-min(len(ordered), int(config["training_window_days"])) :]
        baseline_gmv = _mean([float(row.get("gmv") or 0) for row in recent])
        baseline_purchases = _mean([float(row.get("purchase_count") or 0) for row in recent])
        previous = ordered[-min(len(ordered), horizon * 2) : -horizon] if len(ordered) > horizon else []
        previous_gmv = _mean([float(row.get("gmv") or 0) for row in previous]) if previous else baseline_gmv
        change_rate = (baseline_gmv - previous_gmv) / previous_gmv if previous_gmv else 0.0
        sparse = history_days < int(config["min_history_days"])
        interval_width = 0.65 if sparse else 0.22
        for offset in range(1, horizon + 1):
            forecast_dt = max_dt + timedelta(days=offset)
            multiplier = 1 + min(max(change_rate, -0.25), 0.25) * (offset / horizon)
            point_gmv = max(0.0, baseline_gmv * multiplier)
            point_purchases = max(0.0, baseline_purchases * multiplier)
            results.append(
                {
                    "contract_version": FORECAST_CONTRACT_VERSION,
                    "dt": forecast_dt.isoformat(),
                    "scope": key[0],
                    "entity_key": key[1],
                    "entity_label": ordered[-1]["entity_label"],
                    "metric": "gmv",
                    "forecast_value": round(point_gmv, 2),
                    "lower_bound": round(max(0.0, point_gmv * (1 - interval_width)), 2),
                    "upper_bound": round(point_gmv * (1 + interval_width), 2),
                    "history_days": history_days,
                    "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                    "fallback_reason": "insufficient_history_days" if sparse else "",
                }
            )
            results.append(
                {
                    "contract_version": FORECAST_CONTRACT_VERSION,
                    "dt": forecast_dt.isoformat(),
                    "scope": key[0],
                    "entity_key": key[1],
                    "entity_label": ordered[-1]["entity_label"],
                    "metric": "purchase_count",
                    "forecast_value": round(point_purchases, 2),
                    "lower_bound": round(max(0.0, point_purchases * (1 - interval_width)), 2),
                    "upper_bound": round(point_purchases * (1 + interval_width), 2),
                    "history_days": history_days,
                    "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                    "fallback_reason": "insufficient_history_days" if sparse else "",
                }
            )
    return results


def build_entity_rows(
    daily_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    history_by_entity = select_entities(daily_rows, int(config["top_entities"]))
    forecast_by_entity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in forecast_rows:
        forecast_by_entity.setdefault((row["scope"], row["entity_key"]), []).append(row)
    entities: list[dict[str, Any]] = []
    for key, history in history_by_entity.items():
        forecasts = forecast_by_entity.get(key, [])
        gmv_forecast = sum(float(row["forecast_value"]) for row in forecasts if row["metric"] == "gmv")
        purchase_forecast = sum(float(row["forecast_value"]) for row in forecasts if row["metric"] == "purchase_count")
        recent = sorted(history, key=lambda row: row["dt"])[-int(config["forecast_horizon_days"]) :]
        recent_gmv = sum(float(row.get("gmv") or 0) for row in recent)
        expected_change_rate = round((gmv_forecast - recent_gmv) / recent_gmv, 6) if recent_gmv else 0.0
        sparse = len({row["dt"] for row in history}) < int(config["min_history_days"])
        risk_level = _risk_level(expected_change_rate, sparse, config)
        entities.append(
            {
                "contract_version": FORECAST_CONTRACT_VERSION,
                "scope": key[0],
                "entity_key": key[1],
                "entity_label": history[-1]["entity_label"],
                "forecast_gmv": round(gmv_forecast, 2),
                "forecast_purchase_count": round(purchase_forecast, 2),
                "recent_gmv": round(recent_gmv, 2),
                "expected_change_rate": expected_change_rate,
                "history_days": len({row["dt"] for row in history}),
                "risk_level": risk_level,
                "risk_score": _risk_score(expected_change_rate, sparse),
                "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                "fallback_reason": "insufficient_history_days" if sparse else "",
                "recommended_action": _entity_action(risk_level, sparse),
            }
        )
    return sorted(entities, key=lambda row: (-int(row["risk_score"]), row["scope"], row["entity_key"]))


def build_backtest_rows(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    backtest_window = max([int(config["backtest_window_days"]), *[int(value) for value in config.get("backtest_windows", [])]])
    for key, entity_rows in select_entities(daily_rows, int(config["top_entities"])).items():
        ordered = sorted(entity_rows, key=lambda row: row["dt"])
        if len(ordered) < 2:
            continue
        holdout = ordered[-min(backtest_window, len(ordered) - 1) :]
        train = ordered[: -len(holdout)]
        rolling_baseline = _mean([float(row.get("gmv") or 0) for row in train]) if train else float(ordered[0].get("gmv") or 0)
        for offset, row in enumerate(holdout, start=1):
            row_dt = _parse_date(row["dt"])
            historical = ordered[: ordered.index(row)]
            weekday_history = [
                float(history_row.get("gmv") or 0)
                for history_row in historical
                if _parse_date(history_row["dt"]).weekday() == row_dt.weekday()
            ]
            baseline = _mean(weekday_history[-4:]) if weekday_history else rolling_baseline
            model_name = "weekday_baseline_backtest" if weekday_history else "rolling_baseline_backtest"
            actual = float(row.get("gmv") or 0)
            error = actual - baseline
            rows.append(
                {
                    "contract_version": FORECAST_CONTRACT_VERSION,
                    "dt": row["dt"],
                    "scope": key[0],
                    "entity_key": key[1],
                    "entity_label": row["entity_label"],
                    "metric": "gmv",
                    "actual": round(actual, 2),
                    "forecast": round(baseline, 2),
                    "absolute_error": round(abs(error), 2),
                    "error": round(error, 2),
                    "horizon": offset,
                    "model_name": model_name,
                }
            )
    return rows


def build_backtest_evaluation(backtest_rows: list[dict[str, Any]], config: dict[str, Any], run_id: str) -> dict[str, Any]:
    windows = sorted({int(value) for value in config.get("backtest_windows", []) if int(value) > 0})
    if not windows:
        windows = [int(config["backtest_window_days"])]
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "run_id": run_id,
        "windows": windows,
        "model_metrics": _aggregate_backtest(backtest_rows, lambda row: str(row["model_name"])),
        "horizon_metrics": _aggregate_backtest(backtest_rows, lambda row: f"h{int(row.get('horizon') or 1)}"),
        "window_metrics": [
            {
                "window_days": window,
                **_metric_summary([row for row in backtest_rows if int(row.get("horizon") or 1) <= window]),
            }
            for window in windows
        ],
        "error_distribution": {
            "max_absolute_error": max([float(row["absolute_error"]) for row in backtest_rows], default=0.0),
            "avg_absolute_error": round(_mean([float(row["absolute_error"]) for row in backtest_rows]), 6),
            "backtest_rows": len(backtest_rows),
        },
        "quality_gates": [
            {
                "name": "site_wape",
                "actual": _site_metric(backtest_rows, "wape"),
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": (_site_metric(backtest_rows, "wape") or 1.0) <= float(config["max_site_wape"]),
            },
            {
                "name": "weekday_baseline_available",
                "actual": any(row.get("model_name") == "weekday_baseline_backtest" for row in backtest_rows),
                "operator": "==",
                "expected": True,
                "passed": any(row.get("model_name") == "weekday_baseline_backtest" for row in backtest_rows),
            },
        ],
    }


def _aggregate_backtest(backtest_rows: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in backtest_rows:
        groups.setdefault(key_fn(row), []).append(row)
    return [{"group": key, **_metric_summary(rows)} for key, rows in sorted(groups.items())]


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual_sum = sum(float(row.get("actual") or 0) for row in rows)
    absolute_error_sum = sum(float(row.get("absolute_error") or 0) for row in rows)
    error_sum = sum(float(row.get("error") or 0) for row in rows)
    return {
        "rows": len(rows),
        "actual_sum": round(actual_sum, 2),
        "forecast_sum": round(sum(float(row.get("forecast") or 0) for row in rows), 2),
        "wape": round(absolute_error_sum / actual_sum, 6) if actual_sum else None,
        "bias": round(error_sum / actual_sum, 6) if actual_sum else None,
        "mae": round(absolute_error_sum / len(rows), 6) if rows else None,
    }


def _site_metric(backtest_rows: list[dict[str, Any]], metric: str) -> float | None:
    summary = _metric_summary([row for row in backtest_rows if row.get("scope") == "site"])
    return summary.get(metric)


def build_quality(
    daily_rows: list[dict[str, Any]],
    backtest_rows: list[dict[str, Any]],
    config: dict[str, Any],
    excluded_dates: list[str] | None = None,
    driver_history: dict[str, int] | None = None,
) -> dict[str, Any]:
    driver_history = driver_history or {
        "requested_history_days": int(config["history_collect_days"]),
        "collected_history_days": int(config["history_collect_days"]),
        "max_driver_history_rows": int(config["max_driver_history_rows"]),
        "driver_history_rows": len(daily_rows),
    }
    site_history_days = len({row["dt"] for row in daily_rows if row["scope"] == "site"})
    site_backtest = [row for row in backtest_rows if row["scope"] == "site"]
    actual_sum = sum(float(row["actual"]) for row in site_backtest)
    absolute_error_sum = sum(float(row["absolute_error"]) for row in site_backtest)
    error_sum = sum(float(row["error"]) for row in site_backtest)
    site_wape = round(absolute_error_sum / actual_sum, 6) if actual_sum else None
    site_bias = round(error_sum / actual_sum, 6) if actual_sum else None
    checks = [
        {
            "name": "minimum_history_days",
            "actual": site_history_days,
            "operator": ">=",
            "expected": int(config["min_history_days"]),
            "passed": site_history_days >= int(config["min_history_days"]),
        }
    ]
    checks.append(
        {
            "name": "driver_history_rows",
            "actual": int(driver_history["driver_history_rows"]),
            "operator": "<=",
            "expected": int(driver_history["max_driver_history_rows"]),
            "passed": int(driver_history["driver_history_rows"]) <= int(driver_history["max_driver_history_rows"]),
        }
    )
    if site_wape is not None:
        checks.append(
            {
                "name": "site_wape",
                "actual": site_wape,
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": site_wape <= float(config["max_site_wape"]),
            }
        )
    else:
        checks.append(
            {
                "name": "site_wape",
                "actual": 1.0,
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": False,
            }
        )
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "passed": all(check["passed"] for check in checks),
        "quality_status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "checks": checks,
        "metrics": {
            "site_history_days": site_history_days,
            "site_wape": site_wape,
            "site_bias": site_bias,
            "backtest_rows": len(backtest_rows),
            "sparse_history": site_history_days < int(config["min_history_days"]),
            "excluded_incomplete_dates": excluded_dates or [],
            **driver_history,
        },
    }


def build_risks(entity_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    for row in entity_rows:
        if row["risk_level"] == "low":
            continue
        risks.append(
            {
                "contract_version": FORECAST_CONTRACT_VERSION,
                "risk_id": f"forecast:{row['scope']}:{row['entity_key']}",
                "scope": row["scope"],
                "entity_key": row["entity_key"],
                "entity_label": row["entity_label"],
                "severity": row["risk_level"],
                "risk_type": "insufficient_history" if row["fallback_reason"] else "demand_drop",
                "metric": "gmv",
                "evidence": {
                    "expected_change_rate": row["expected_change_rate"],
                    "history_days": row["history_days"],
                    "forecast_gmv": row["forecast_gmv"],
                },
                "recommended_action": row["recommended_action"],
            }
        )
    return sorted(risks, key=lambda row: (0 if row["severity"] == "high" else 1, row["entity_key"]))


def build_summary(
    daily_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    entity_rows: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
    driver_history: dict[str, int] | None = None,
) -> dict[str, Any]:
    site_forecast = [row for row in forecast_rows if row["scope"] == "site"]
    site_gmv = sum(float(row["forecast_value"]) for row in site_forecast if row["metric"] == "gmv")
    site_purchases = sum(float(row["forecast_value"]) for row in site_forecast if row["metric"] == "purchase_count")
    history_dates = sorted({row["dt"] for row in daily_rows if row["scope"] == "site"})
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "forecast_horizon_days": int(config["forecast_horizon_days"]),
        "training_window_days": int(config["training_window_days"]),
        "backtest_window_days": int(config["backtest_window_days"]),
        "history_days": len(history_dates),
        "driver_history_rows": int((driver_history or {}).get("driver_history_rows") or 0),
        "max_driver_history_rows": int((driver_history or {}).get("max_driver_history_rows") or config["max_driver_history_rows"]),
        "history_range": {"min_dt": history_dates[0] if history_dates else None, "max_dt": history_dates[-1] if history_dates else None},
        "entity_count": len(entity_rows),
        "site_forecast_gmv": round(site_gmv, 2),
        "site_forecast_purchase_count": round(site_purchases, 2),
        "risk_count": len(risks),
        "high_risk_count": len([row for row in risks if row["severity"] == "high"]),
        "quality_status": quality["quality_status"],
        "top_risk": risks[0] if risks else None,
        "recommended_action": "Use forecast risks as planning signals; do not treat sparse-history forecasts as causal or high-confidence predictions.",
    }


def select_entities(rows: list[dict[str, Any]], top_entities: int) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["scope"], row["entity_key"]), []).append(row)
    category_scores = sorted(
        [
            (sum(float(row.get("gmv") or 0) for row in entity_rows), key)
            for key, entity_rows in grouped.items()
            if key[0] == "category"
        ],
        reverse=True,
    )
    keep = {("site", "all")}
    keep.update(key for _, key in category_scores[:top_entities])
    return {key: entity_rows for key, entity_rows in grouped.items() if key in keep}


def _risk_level(expected_change_rate: float, sparse: bool, config: dict[str, Any]) -> str:
    if sparse or expected_change_rate <= float(config["high_risk_drop_rate"]):
        return "high"
    if expected_change_rate <= float(config["medium_risk_drop_rate"]):
        return "medium"
    return "low"


def _risk_score(expected_change_rate: float, sparse: bool) -> int:
    if sparse:
        return 85
    return min(100, max(0, int(abs(min(expected_change_rate, 0)) * 400)))


def _entity_action(risk_level: str, sparse: bool) -> str:
    if sparse:
        return "Collect more history or reduce forecast granularity before committing spend."
    if risk_level == "high":
        return "Review merchandising plan, recommendation coverage, and experiment exposure before the forecast window."
    if risk_level == "medium":
        return "Monitor category demand and prepare a constrained promotion or recommendation adjustment."
    return "Use as baseline demand for planning."


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
