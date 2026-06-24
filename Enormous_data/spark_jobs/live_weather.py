from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

from spark_jobs.cleaning import clean_events
from spark_jobs.main import config_hash, load_config, resolve_input_path
from spark_jobs.readers import read_events
from spark_jobs.session import build_spark
from spark_jobs.writers import write_json_atomic, write_metric_files


LIVE_WEATHER_CONTRACT_VERSION = "live-weather-training/v1"
DEFAULT_TOP_CATEGORIES = 8
DEFAULT_BACKTEST_DAYS = 7
DEFAULT_JOIN_COVERAGE_WARNING = 0.9


WEATHER_SCHEMA = T.StructType(
    [
        T.StructField("time", T.StringType(), True),
        T.StructField("city", T.StringType(), True),
        T.StructField("latitude", T.DoubleType(), True),
        T.StructField("longitude", T.DoubleType(), True),
        T.StructField("temperature_2m", T.DoubleType(), True),
        T.StructField("relative_humidity_2m", T.DoubleType(), True),
        T.StructField("precipitation", T.DoubleType(), True),
        T.StructField("rain", T.DoubleType(), True),
        T.StructField("weather_code", T.DoubleType(), True),
        T.StructField("wind_speed_10m", T.DoubleType(), True),
    ]
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_live_weather_outputs(
    cleaned_df: DataFrame,
    weather_history_path: str | Path,
    current_weather: dict[str, Any],
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
    forecast_weather: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spark = cleaned_df.sparkSession
    top_categories = int(config.get("live_weather", {}).get("top_categories", DEFAULT_TOP_CATEGORIES))
    backtest_days = int(config.get("live_weather", {}).get("backtest_days", DEFAULT_BACKTEST_DAYS))
    warning_threshold = float(config.get("live_weather", {}).get("min_join_coverage_rate", DEFAULT_JOIN_COVERAGE_WARNING))
    city = str(config.get("live_weather", {}).get("city", current_weather.get("city") or "上海"))

    daily_demand = build_daily_demand(cleaned_df, top_categories)
    weather_daily = read_weather_daily(spark, weather_history_path)
    joined = join_demand_weather(daily_demand, weather_daily)
    joined_rows = [_json_safe(row.asDict()) for row in joined.orderBy("scope", "entity_key", "dt").collect()]
    ecommerce_rows = daily_demand.count()
    weather_rows = weather_daily.count()
    joined_count = len(joined_rows)
    coverage = round(joined_count / ecommerce_rows, 6) if ecommerce_rows else 0.0
    quality_status = "passed" if coverage >= warning_threshold else "needs_review"

    baseline_rows, enhanced_rows = build_backtest_rows(joined_rows, backtest_days)
    comparison = build_comparison_metrics(baseline_rows, enhanced_rows, run_id)
    series = build_series_rows(baseline_rows, enhanced_rows)
    impact = build_current_weather_impact(joined_rows, current_weather, comparison, run_id)
    warnings = []
    if coverage < warning_threshold:
        warnings.append("low_weather_join_coverage")
    if current_weather.get("source_status") == "unavailable":
        warnings.append("current_weather_unavailable")

    date_values = [row["dt"] for row in joined_rows]
    weather_dates = [row["dt"] for row in [_json_safe(row.asDict()) for row in weather_daily.select("dt").distinct().collect()]]
    summary = {
        "contract_version": LIVE_WEATHER_CONTRACT_VERSION,
        "run_id": run_id,
        "city": city,
        "time_grain": "daily",
        "quality_status": quality_status,
        "source_status": current_weather.get("source_status", "unknown"),
        "weather_rows": weather_rows,
        "ecommerce_agg_rows": ecommerce_rows,
        "joined_rows": joined_count,
        "join_coverage_rate": coverage,
        "missing_weather_rate": round(1 - coverage, 6) if ecommerce_rows else 0.0,
        "ecommerce_date_range": _range(date_values),
        "weather_date_range": _range(weather_dates),
        "input_snapshot": input_snapshot,
        "current_weather_used_for_training": False,
        "warning_threshold": warning_threshold,
        "warnings": warnings,
        "generated_at": utc_now(),
    }
    outputs = {
        "live_weather_summary": summary,
        "live_training_metrics": comparison,
        "live_weather_impact": impact,
        "live_weather_series": series,
    }
    if forecast_weather:
        outputs["live_weather_forecast_impact"] = build_forecast_weather_impact(
            joined_rows,
            forecast_weather,
            run_id=run_id,
            horizon_hours=int(config.get("live_weather", {}).get("forecast_horizon_hours", 24)),
        )
    return outputs


def build_forecast_weather_impact(
    joined_rows: list[dict[str, Any]],
    forecast_weather: dict[str, Any],
    *,
    run_id: str,
    horizon_hours: int = 24,
) -> dict[str, Any]:
    forecast_rows = (forecast_weather.get("hourly") or [])[:horizon_hours]
    category_groups = {
        entity_key: rows
        for entity_key, rows in _group_entities(joined_rows).items()
        if entity_key[0] == "category" and rows
    }
    items = []
    for forecast_row in forecast_rows:
        features = {
            "temperature_2m": _float(forecast_row.get("temperature_2m")),
            "relative_humidity_2m": _float(forecast_row.get("relative_humidity_2m")),
            "precipitation": _float(forecast_row.get("precipitation")),
            "rain": _float(forecast_row.get("rain")),
            "weather_code": _float(forecast_row.get("weather_code")),
            "wind_speed_10m": _float(forecast_row.get("wind_speed_10m")),
        }
        category_impacts = []
        for entity_key, rows in category_groups.items():
            factor, components = _weather_factor_details(rows, {**rows[-1], **features})
            score = round((factor - 1.0) * 100, 2)
            category_impacts.append(
                {
                    "entity_key": entity_key[1],
                    "entity_label": rows[-1]["entity_label"],
                    "impact_score": score,
                    "demand_multiplier": round(factor, 4),
                    "direction": "up" if score > 1 else "down" if score < -1 else "neutral",
                    "impact_components": {key: round(value * 100, 2) for key, value in components.items() if math.isfinite(value)},
                    "reason": _impact_reason(rows[-1]["entity_label"], features, factor, components),
                }
            )
        category_impacts = sorted(category_impacts, key=lambda row: abs(float(row["impact_score"])), reverse=True)
        strongest = category_impacts[0] if category_impacts else None
        avg_score = _mean([float(row["impact_score"]) for row in category_impacts]) if category_impacts else 0.0
        items.append(
            {
                "time": forecast_row.get("time"),
                "temperature_2m": features["temperature_2m"],
                "relative_humidity_2m": features["relative_humidity_2m"],
                "precipitation": features["precipitation"],
                "rain": features["rain"],
                "weather_code": features["weather_code"],
                "wind_speed_10m": features["wind_speed_10m"],
                "avg_impact_score": round(avg_score, 2),
                "strongest_category": strongest.get("entity_label") if strongest else None,
                "strongest_impact_score": strongest.get("impact_score") if strongest else None,
                "category_impacts": category_impacts[:8],
            }
        )
    return {
        "contract_version": "live-weather-forecast-impact/v1",
        "run_id": run_id,
        "city": forecast_weather.get("city", "上海"),
        "source_status": forecast_weather.get("source_status", "unknown"),
        "horizon_hours": horizon_hours,
        "generated_at": utc_now(),
        "training_uses_forecast_weather": False,
        "forecast_weather_time_range": _range([str(row.get("time") or "")[:16] for row in items]),
        "summary": _forecast_impact_summary(items),
        "items": items,
    }


def build_daily_demand(cleaned_df: DataFrame, top_categories: int) -> DataFrame:
    purchase = F.col("event_type") == "purchase"
    base = cleaned_df.withColumn("dt", F.to_date("event_timestamp"))
    site = (
        base.groupBy("dt")
        .agg(
            F.count("*").alias("events"),
            F.countDistinct("user_session").alias("sessions"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("site"))
        .withColumn("entity_key", F.lit("all"))
        .withColumn("entity_label", F.lit("全站"))
    )
    category_all = (
        base.groupBy("dt", "category_level1")
        .agg(
            F.count("*").alias("events"),
            F.countDistinct("user_session").alias("sessions"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("category"))
        .withColumnRenamed("category_level1", "entity_key")
        .withColumn("entity_label", F.col("entity_key"))
    )
    top = (
        category_all.groupBy("entity_key")
        .agg(F.sum("gmv").alias("entity_gmv"))
        .orderBy(F.desc("entity_gmv"), "entity_key")
        .limit(top_categories)
        .select("entity_key")
    )
    category = category_all.join(top, "entity_key", "inner")
    return (
        site.unionByName(category)
        .withColumn("dt", F.date_format("dt", "yyyy-MM-dd"))
        .select("dt", "scope", "entity_key", "entity_label", "events", "sessions", "purchase_count", "gmv", "views")
    )


def read_weather_daily(spark, weather_history_path: str | Path) -> DataFrame:
    weather = (
        spark.read.option("header", True)
        .schema(WEATHER_SCHEMA)
        .csv(str(weather_history_path))
        .withColumn("weather_ts", F.to_timestamp("time", "yyyy-MM-dd'T'HH:mm"))
        .withColumn("dt", F.date_format(F.to_date("weather_ts"), "yyyy-MM-dd"))
    )
    return (
        weather.groupBy("dt")
        .agg(
            F.first("city", ignorenulls=True).alias("city"),
            F.avg("temperature_2m").alias("temperature_2m"),
            F.avg("relative_humidity_2m").alias("relative_humidity_2m"),
            F.sum(F.coalesce("precipitation", F.lit(0.0))).alias("precipitation"),
            F.sum(F.coalesce("rain", F.lit(0.0))).alias("rain"),
            F.avg("weather_code").alias("weather_code"),
            F.avg("wind_speed_10m").alias("wind_speed_10m"),
        )
        .select("dt", "city", "temperature_2m", "relative_humidity_2m", "precipitation", "rain", "weather_code", "wind_speed_10m")
    )


def join_demand_weather(daily_demand: DataFrame, weather_daily: DataFrame) -> DataFrame:
    return daily_demand.join(weather_daily, "dt", "inner")


def build_backtest_rows(joined_rows: list[dict[str, Any]], backtest_days: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_rows: list[dict[str, Any]] = []
    enhanced_rows: list[dict[str, Any]] = []
    for entity_key, rows in _group_entities(joined_rows).items():
        ordered = sorted(rows, key=lambda row: row["dt"])
        if len(ordered) < 3:
            continue
        holdout = ordered[-min(backtest_days, len(ordered) - 1) :]
        for holdout_row in holdout:
            train = [row for row in ordered if row["dt"] < holdout_row["dt"]]
            if not train:
                continue
            baseline = _baseline_forecast(train, holdout_row)
            factor = _weather_factor(train, holdout_row)
            enhanced = baseline * factor
            common = {
                "contract_version": LIVE_WEATHER_CONTRACT_VERSION,
                "dt": holdout_row["dt"],
                "scope": holdout_row["scope"],
                "entity_key": holdout_row["entity_key"],
                "entity_label": holdout_row["entity_label"],
                "actual": round(float(holdout_row.get("gmv") or 0.0), 2),
                "weather_factor": round(factor, 4),
            }
            baseline_rows.append(
                {
                    **common,
                    "model_name": "baseline_history",
                    "forecast": round(baseline, 2),
                    "absolute_error": round(abs(float(holdout_row.get("gmv") or 0.0) - baseline), 2),
                }
            )
            enhanced_rows.append(
                {
                    **common,
                    "model_name": "weather_enhanced",
                    "forecast": round(enhanced, 2),
                    "absolute_error": round(abs(float(holdout_row.get("gmv") or 0.0) - enhanced), 2),
                }
            )
    return baseline_rows, enhanced_rows


def build_comparison_metrics(baseline_rows: list[dict[str, Any]], enhanced_rows: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    baseline = _metric_summary(baseline_rows)
    enhanced = _metric_summary(enhanced_rows)
    wape_delta = _delta(baseline.get("wape"), enhanced.get("wape"))
    mae_delta = _delta(baseline.get("mae"), enhanced.get("mae"))
    improved = bool(wape_delta is not None and wape_delta > 0)
    return {
        "contract_version": LIVE_WEATHER_CONTRACT_VERSION,
        "run_id": run_id,
        "generated_at": utc_now(),
        "comparison_status": "improved" if improved else "no_significant_lift",
        "interpretation": "天气特征降低了回测 WAPE。" if improved else "天气特征未显著降低回测误差，本轮仅作为解释性增强信号。",
        "model_metrics": [
            {"model_name": "baseline_history", **baseline},
            {"model_name": "weather_enhanced", **enhanced},
        ],
        "lift": {
            "wape_reduction": wape_delta,
            "mae_reduction": mae_delta,
            "improved": improved,
        },
        "quality_gates": [
            {
                "name": "weather_enhanced_wape_available",
                "actual": enhanced.get("wape"),
                "operator": "is_not",
                "expected": None,
                "passed": enhanced.get("wape") is not None,
            },
            {
                "name": "no_time_travel",
                "actual": "current_weather_excluded_from_training",
                "operator": "==",
                "expected": "current_weather_excluded_from_training",
                "passed": True,
            },
        ],
    }


def build_series_rows(baseline_rows: list[dict[str, Any]], enhanced_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return baseline_rows + enhanced_rows


def build_current_weather_impact(
    joined_rows: list[dict[str, Any]],
    current_weather: dict[str, Any],
    metrics: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    current = current_weather.get("current") or {}
    current_features = {
        "temperature_2m": _float(current.get("temperature_2m")),
        "relative_humidity_2m": _float(current.get("relative_humidity_2m")),
        "precipitation": _float(current.get("precipitation")),
        "rain": _float(current.get("rain")),
        "weather_code": _float(current.get("weather_code")),
        "wind_speed_10m": _float(current.get("wind_speed_10m")),
    }
    impacts = []
    for entity_key, rows in _group_entities(joined_rows).items():
        if entity_key[0] != "category" or not rows:
            continue
        factor, components = _weather_factor_details(rows, {**rows[-1], **current_features})
        score = round((factor - 1.0) * 100, 2)
        impacts.append(
            {
                "scope": "category",
                "entity_key": entity_key[1],
                "entity_label": rows[-1]["entity_label"],
                "impact_score": score,
                "demand_multiplier": round(factor, 4),
                "recommendation_weight": round(max(0.75, min(1.25, factor)), 4),
                "direction": "up" if score > 1 else "down" if score < -1 else "neutral",
                "impact_components": {key: round(value * 100, 2) for key, value in components.items() if math.isfinite(value)},
                "reason": _impact_reason(rows[-1]["entity_label"], current_features, factor, components),
            }
        )
    impacts = sorted(impacts, key=lambda row: abs(float(row["impact_score"])), reverse=True)[:8]
    return {
        "contract_version": LIVE_WEATHER_CONTRACT_VERSION,
        "run_id": run_id,
        "city": current_weather.get("city", "上海"),
        "source_status": current_weather.get("source_status", "unknown"),
        "current_weather": current_features,
        "current_weather_time": current.get("time"),
        "generated_at": utc_now(),
        "training_uses_current_weather": False,
        "comparison_status": metrics.get("comparison_status"),
        "items": impacts,
    }


def _baseline_forecast(train: list[dict[str, Any]], holdout_row: dict[str, Any]) -> float:
    target_weekday = datetime.strptime(holdout_row["dt"], "%Y-%m-%d").weekday()
    weekday_values = [
        float(row.get("gmv") or 0.0)
        for row in train
        if datetime.strptime(row["dt"], "%Y-%m-%d").weekday() == target_weekday
    ]
    if weekday_values:
        return _mean(weekday_values[-4:])
    return _mean([float(row.get("gmv") or 0.0) for row in train[-14:]])


def _weather_factor(train: list[dict[str, Any]], target_row: dict[str, Any]) -> float:
    return _weather_factor_details(train, target_row)[0]


def _weather_factor_details(train: list[dict[str, Any]], target_row: dict[str, Any]) -> tuple[float, dict[str, float]]:
    train_gmv = [float(row.get("gmv") or 0.0) for row in train]
    baseline = _mean(train_gmv)
    if baseline <= 0:
        return 1.0, {}
    demand_index = [value / baseline for value in train_gmv]
    temp_values = [float(row.get("temperature_2m") or 0.0) for row in train]
    wind_values = [float(row.get("wind_speed_10m") or 0.0) for row in train]
    humidity_values = [float(row.get("relative_humidity_2m") or 0.0) for row in train]
    code_values = [float(row.get("weather_code") or 0.0) for row in train]
    wet_values = [demand_index[index] for index, row in enumerate(train) if float(row.get("precipitation") or 0.0) > 0]
    dry_values = [demand_index[index] for index, row in enumerate(train) if float(row.get("precipitation") or 0.0) <= 0]

    components: dict[str, float] = {}
    if wet_values and dry_values and float(target_row.get("precipitation") or 0.0) > 0:
        wet_component = (_bounded_ratio(_mean(wet_values), _mean(dry_values), 0.82, 1.18) - 1.0) * 0.9
        components["降雨"] = wet_component
    if temp_values:
        components["温度"] = _pearson(temp_values, demand_index) * _bounded_z(
            float(target_row.get("temperature_2m") or _mean(temp_values)), temp_values
        ) * 0.07
    if humidity_values:
        components["湿度"] = _pearson(humidity_values, demand_index) * _bounded_z(
            float(target_row.get("relative_humidity_2m") or _mean(humidity_values)), humidity_values
        ) * 0.045
    if wind_values:
        components["风速"] = _pearson(wind_values, demand_index) * _bounded_z(
            float(target_row.get("wind_speed_10m") or _mean(wind_values)), wind_values
        ) * 0.035
    if code_values:
        components["天气码"] = _pearson(code_values, demand_index) * _bounded_z(
            float(target_row.get("weather_code") or _mean(code_values)), code_values
        ) * 0.025

    raw_adjustment = sum(value for value in components.values() if math.isfinite(value))
    factor = max(0.75, min(1.25, 1.0 + raw_adjustment))
    return factor, components


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual_sum = sum(abs(float(row.get("actual") or 0.0)) for row in rows)
    abs_error = sum(float(row.get("absolute_error") or 0.0) for row in rows)
    return {
        "rows": len(rows),
        "wape": round(abs_error / actual_sum, 6) if actual_sum else None,
        "mae": round(abs_error / len(rows), 6) if rows else None,
        "actual_sum": round(actual_sum, 2),
        "absolute_error_sum": round(abs_error, 2),
    }


def _group_entities(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["scope"]), str(row["entity_key"])), []).append(row)
    return grouped


def _range(values: list[str]) -> dict[str, str | None]:
    clean = sorted(value for value in values if value)
    return {"min": clean[0] if clean else None, "max": clean[-1] if clean else None}


def _mean(values: list[float]) -> float:
    clean = [value for value in values if math.isfinite(value)]
    return sum(clean) / len(clean) if clean else 0.0


def _std(values: list[float]) -> float:
    avg = _mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values)) if values else 0.0


def _bounded_z(value: float, values: list[float]) -> float:
    std = _std(values)
    if std <= 0:
        return 0.0
    return max(-2.0, min(2.0, (value - _mean(values)) / std))


def _bounded_ratio(numerator: float, denominator: float, low: float, high: float) -> float:
    if denominator <= 0:
        return 1.0
    return max(low, min(high, numerator / denominator))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        return 0.0
    x_avg = _mean(xs)
    y_avg = _mean(ys)
    numerator = sum((x - x_avg) * (y - y_avg) for x, y in zip(xs, ys))
    x_var = sum((x - x_avg) ** 2 for x in xs)
    y_var = sum((y - y_avg) ** 2 for y in ys)
    if x_var <= 0 or y_var <= 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / math.sqrt(x_var * y_var)))


def _delta(baseline: float | None, enhanced: float | None) -> float | None:
    if baseline is None or enhanced is None:
        return None
    return round(baseline - enhanced, 6)


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _impact_reason(
    entity_label: str,
    current_features: dict[str, float | None],
    factor: float,
    components: dict[str, float] | None = None,
) -> str:
    reasons = []
    if (current_features.get("precipitation") or 0) > 0:
        reasons.append("当前有降水")
    if current_features.get("temperature_2m") is not None:
        reasons.append(f"温度 {current_features['temperature_2m']:.1f}°C")
    if current_features.get("wind_speed_10m") is not None:
        reasons.append(f"风速 {current_features['wind_speed_10m']:.1f}km/h")
    drivers = _component_drivers(components or {})
    if drivers:
        reasons.append(f"{entity_label} 历史响应：{'；'.join(drivers)}")
    direction = "上调" if factor > 1.01 else "下调" if factor < 0.99 else "保持"
    score = (factor - 1.0) * 100
    return f"{'，'.join(reasons) or '当前天气信号可用'}，综合影响 {score:+.2f}%，建议{direction}类目需求权重。"


def _component_drivers(components: dict[str, float]) -> list[str]:
    clean = {key: value for key, value in components.items() if math.isfinite(value) and abs(value) >= 0.002}
    if not clean:
        return []
    drivers = []
    for key, value in sorted(clean.items(), key=lambda item: abs(item[1]), reverse=True)[:2]:
        drivers.append(f"{key}{'正向' if value > 0 else '负向'} {value * 100:+.2f}%")
    return drivers


def _forecast_impact_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "max_negative_hour": None,
            "max_positive_hour": None,
            "peak_abs_hour": None,
            "peak_abs_impact_score": None,
            "dominant_driver": None,
        }
    negative = min(items, key=lambda row: float(row.get("avg_impact_score") or 0.0))
    positive = max(items, key=lambda row: float(row.get("avg_impact_score") or 0.0))
    peak = max(items, key=lambda row: abs(float(row.get("strongest_impact_score") or row.get("avg_impact_score") or 0.0)))
    driver_counts: dict[str, int] = {}
    for item in items:
        for category in item.get("category_impacts") or []:
            for key in (category.get("impact_components") or {}).keys():
                driver_counts[key] = driver_counts.get(key, 0) + 1
    dominant_driver = max(driver_counts.items(), key=lambda item: item[1])[0] if driver_counts else None
    return {
        "max_negative_hour": negative.get("time"),
        "max_negative_avg_impact_score": negative.get("avg_impact_score"),
        "max_positive_hour": positive.get("time"),
        "max_positive_avg_impact_score": positive.get("avg_impact_score"),
        "peak_abs_hour": peak.get("time"),
        "peak_abs_category": peak.get("strongest_category"),
        "peak_abs_impact_score": peak.get("strongest_impact_score"),
        "dominant_driver": dominant_driver,
    }


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in payload.items():
        if hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def run_job(
    config: dict[str, Any],
    *,
    weather_history_path: str | Path,
    current_weather_path: str | Path,
    forecast_weather_path: str | Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or uuid4().hex
    started = time.perf_counter()
    spark_config = config.get("spark", {})
    data_config = config.get("data", {})
    output_dir = Path(data_config.get("output_dir", "data/cache"))
    spark = build_spark(
        app_name=f"{config.get('app', {}).get('name', 'ecommerce-behavior-dashboard')}-live-weather",
        master=spark_config.get("master"),
        configs={
            **spark_config.get("configs", {}),
            "spark.sql.shuffle.partitions": spark_config.get("shuffle_partitions", 4),
            "spark.sql.session.timeZone": spark_config.get("timezone", "Asia/Shanghai"),
            "spark.sql.adaptive.enabled": "true",
        },
    )
    try:
        actual_input_path = resolve_input_path(config)
        source_df = read_events(
            spark,
            input_path=actual_input_path,
            input_format=data_config.get("input_format", "csv"),
            delimiter=data_config.get("delimiter", ","),
        )
        raw_df = source_df.limit(int(data_config["limit"])) if data_config.get("limit") else source_df
        cleaned_df = clean_events(raw_df)
        with Path(current_weather_path).open("r", encoding="utf-8") as handle:
            import json

            current_weather = json.load(handle)
        forecast_weather = None
        if forecast_weather_path and Path(forecast_weather_path).exists():
            with Path(forecast_weather_path).open("r", encoding="utf-8") as handle:
                forecast_weather = json.load(handle)
        input_snapshot = {
            "configured_input_path": data_config["input_path"],
            "actual_input_path": actual_input_path,
            "input_format": data_config.get("input_format", "csv"),
            "weather_history_path": str(weather_history_path),
            "current_weather_path": str(current_weather_path),
            "forecast_weather_path": str(forecast_weather_path) if forecast_weather_path else None,
        }
        metrics = build_live_weather_outputs(
            cleaned_df,
            weather_history_path,
            current_weather,
            config,
            run_id=run_id,
            input_snapshot=input_snapshot,
            forecast_weather=forecast_weather,
        )
        elapsed_seconds = round(time.perf_counter() - started, 3)
        status = {
            "contract_version": LIVE_WEATHER_CONTRACT_VERSION,
            "run_id": run_id,
            "job_type": "live_weather_training",
            "status": "succeeded",
            "quality_status": metrics["live_weather_summary"]["quality_status"],
            "elapsed_seconds": elapsed_seconds,
            "started_at": None,
            "finished_at": utc_now(),
            "message": "live weather training finished",
            "config_hash": config_hash(config),
            "output_artifacts": {
                "summary": str(output_dir / "live_weather_summary.json"),
                "metrics": str(output_dir / "live_training_metrics.json"),
                "impact": str(output_dir / "live_weather_impact.json"),
                "forecast_impact": str(output_dir / "live_weather_forecast_impact.json"),
                "series": str(output_dir / "live_weather_series.json"),
            },
        }
        metrics["live_training_status"] = status
        write_metric_files(output_dir, metrics)
        return metrics
    finally:
        spark.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build live weather enhanced training metrics.")
    parser.add_argument("--config", default="configs/local.yaml")
    parser.add_argument("--weather-history", default="data/live/weather_history_2019.csv")
    parser.add_argument("--current-weather", default="data/live/current_weather.json")
    parser.add_argument("--forecast-weather", default="data/live/forecast_weather_24h.json")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = run_job(
        load_config(args.config),
        weather_history_path=args.weather_history,
        current_weather_path=args.current_weather,
        forecast_weather_path=args.forecast_weather,
        run_id=args.run_id,
    )
    print(f"Live weather training finished: run_id={metrics['live_training_status']['run_id']}")


if __name__ == "__main__":
    main()
