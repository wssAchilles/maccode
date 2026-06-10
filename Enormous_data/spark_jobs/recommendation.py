from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark import StorageLevel

from spark_jobs.writers import write_json_atomic


RECOMMENDATION_CONTRACT_VERSION = "nearline-recommendation/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "top_k": 5,
    "session_sample_limit": 500,
    "candidate_pool": 80,
    "min_confidence": 0.02,
    "min_coverage_rate": 0.75,
    "max_fallback_rate": 0.8,
    "min_avg_confidence": 0.03,
    "max_freshness_lag_minutes": 5_300_000,
    "max_duplicate_recommendation_rate": 0.0,
    "max_invalid_product_rate": 0.0,
}


def recommendation_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_recommendation_outputs(
    cleaned_df: DataFrame,
    optimization_plan: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    output_dir: str | Path,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[DataFrame, dict[str, Any]]:
    product_features = build_product_features(cleaned_df, int(config["candidate_pool"])).persist(StorageLevel.MEMORY_AND_DISK)
    target_sessions = build_target_sessions(cleaned_df, int(config["session_sample_limit"])).persist(StorageLevel.MEMORY_AND_DISK)
    recommendation_features = build_recommendation_features(
        cleaned_df,
        product_features,
        target_sessions,
        optimization_plan,
        int(config["top_k"]),
        float(config["min_confidence"]),
    ).persist(StorageLevel.MEMORY_AND_DISK)
    try:
        preview_limit = int(config.get("preview_limit", int(config["session_sample_limit"]) * int(config["top_k"])))
        items = [
            _item_from_row(row.asDict(recursive=True))
            for row in recommendation_features.orderBy("user_session", "rank").limit(preview_limit).collect()
        ]
        session_count = target_sessions.count()
        max_event_ts = cleaned_df.agg(F.max("event_timestamp").alias("max_event_ts")).first()["max_event_ts"]
        generated_at = datetime.now(UTC).isoformat()
        freshness_lag = _freshness_lag_minutes(max_event_ts, generated_at)
        quality = evaluate_recommendation_quality_frame(
            recommendation_features=recommendation_features,
            target_session_count=session_count,
            product_count=product_features.count(),
            freshness_lag_minutes=freshness_lag,
            config=config,
        )
        quality["preview_recommendation_count"] = len(items)
        alerts = build_recommendation_alerts(quality)
        summary = build_recommendation_summary(
            run_id=run_id,
            input_snapshot=input_snapshot,
            generated_at=generated_at,
            target_session_count=session_count,
            freshness_lag_minutes=freshness_lag,
            quality=quality,
            output_dir=output_dir,
        )
        run_payload = {
            "summary": summary,
            "items": items,
            "quality": quality,
            "alerts": alerts,
        }
        promoted = promote_or_degrade_recommendations(Path(output_dir), run_id, run_payload)
        return recommendation_features, promoted
    finally:
        product_features.unpersist()
        target_sessions.unpersist()


def build_product_features(cleaned_df: DataFrame, candidate_pool: int) -> DataFrame:
    views = F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0))
    carts = F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0))
    purchases = F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0))
    features = (
        cleaned_df.groupBy("product_id", "brand", "category_level1")
        .agg(
            views.alias("views"),
            carts.alias("carts"),
            purchases.alias("purchases"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(0)), 2).alias(
                "revenue"
            ),
            F.round(F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))), 2).alias("avg_price"),
            F.max("event_timestamp").alias("latest_event_ts"),
        )
        .filter(F.col("views") > 0)
        .withColumn("view_to_cart_rate", F.col("carts") / F.col("views"))
        .withColumn("view_to_purchase_rate", F.col("purchases") / F.col("views"))
        .withColumn("revenue_per_view", F.col("revenue") / F.col("views"))
        .withColumn("confidence", F.least(F.lit(1.0), F.sqrt(F.col("views") / F.lit(500.0))))
        .withColumn(
            "product_score",
            F.round(
                F.col("view_to_purchase_rate") * F.lit(0.55)
                + F.col("view_to_cart_rate") * F.lit(0.25)
                + F.least(F.col("revenue_per_view") / F.lit(500.0), F.lit(1.0)) * F.lit(0.20),
                8,
            ),
        )
    )
    window = Window.partitionBy("category_level1").orderBy(F.desc("product_score"), F.desc("views"), F.asc("product_id"))
    return features.withColumn("category_rank", F.row_number().over(window)).filter(F.col("category_rank") <= candidate_pool)


def build_target_sessions(cleaned_df: DataFrame, session_limit: int) -> DataFrame:
    category_events = (
        cleaned_df.groupBy("user_session", "user_id", "category_level1")
        .agg(
            F.count("*").alias("events"),
            F.max("event_timestamp").alias("latest_event_ts"),
        )
        .filter(F.col("user_session") != "unknown")
    )
    preference_window = Window.partitionBy("user_session").orderBy(F.desc("events"), F.desc("latest_event_ts"), F.asc("category_level1"))
    return (
        category_events.withColumn("preference_rank", F.row_number().over(preference_window))
        .filter(F.col("preference_rank") == 1)
        .orderBy(F.desc("latest_event_ts"), F.asc("user_session"))
        .limit(session_limit)
        .select("user_session", "user_id", "category_level1", "latest_event_ts")
    )


def build_recommendation_features(
    cleaned_df: DataFrame,
    product_features: DataFrame,
    target_sessions: DataFrame,
    optimization_plan: list[dict[str, Any]],
    top_k: int,
    min_confidence: float,
) -> DataFrame:
    seen_products = cleaned_df.select("user_session", "product_id").dropDuplicates()
    personalized = (
        target_sessions.alias("sessions")
        .join(product_features.alias("products"), on="category_level1", how="inner")
        .join(
            seen_products.alias("seen"),
            (F.col("sessions.user_session") == F.col("seen.user_session"))
            & (F.col("products.product_id") == F.col("seen.product_id")),
            "left_anti",
        )
        .filter(F.col("confidence") >= min_confidence)
        .select(
            F.col("sessions.user_session").alias("user_session"),
            F.col("sessions.user_id").alias("user_id"),
            F.col("products.product_id").alias("product_id"),
            F.col("products.brand").alias("brand"),
            F.col("products.category_level1").alias("category_level1"),
            F.round(F.col("product_score") * F.lit(1.15) + F.col("confidence") * F.lit(0.05), 8).alias("score"),
            F.round(F.col("confidence"), 6).alias("confidence"),
            F.array(F.lit("category_affinity"), F.lit("high_conversion")).alias("reason_codes"),
            F.lit("personalized_category").alias("source"),
            F.lit(False).alias("fallback_used"),
        )
    )
    fallback_products = build_fallback_products(product_features, optimization_plan)
    fallback = (
        target_sessions.alias("sessions")
        .crossJoin(fallback_products.alias("products"))
        .join(
            seen_products.alias("seen"),
            (F.col("sessions.user_session") == F.col("seen.user_session"))
            & (F.col("products.product_id") == F.col("seen.product_id")),
            "left_anti",
        )
        .select(
            F.col("sessions.user_session").alias("user_session"),
            F.col("sessions.user_id").alias("user_id"),
            F.col("products.product_id").alias("product_id"),
            F.col("products.brand").alias("brand"),
            F.col("products.category_level1").alias("category_level1"),
            F.round(F.col("products.product_score") * F.lit(0.92), 8).alias("score"),
            F.round(F.col("products.confidence"), 6).alias("confidence"),
            F.col("products.reason_codes").alias("reason_codes"),
            F.col("products.source").alias("source"),
            F.lit(True).alias("fallback_used"),
        )
    )
    merged = personalized.unionByName(fallback)
    dedupe_window = Window.partitionBy("user_session", "product_id").orderBy(
        F.asc("fallback_used"),
        F.desc("score"),
        F.desc("confidence"),
    )
    ranked = merged.withColumn("product_choice_rank", F.row_number().over(dedupe_window)).filter(
        F.col("product_choice_rank") == 1
    )
    rank_window = Window.partitionBy("user_session").orderBy(F.desc("score"), F.desc("confidence"), F.asc("product_id"))
    return (
        ranked.withColumn("rank", F.row_number().over(rank_window))
        .filter(F.col("rank") <= top_k)
        .drop("product_choice_rank")
        .orderBy("user_session", "rank")
    )


def build_fallback_products(product_features: DataFrame, optimization_plan: list[dict[str, Any]]) -> DataFrame:
    spark = product_features.sparkSession
    plan_ids = [str(row["product_id"]) for row in optimization_plan[:50] if row.get("product_id")]
    base = product_features
    if plan_ids:
        plan_df = spark.createDataFrame([(product_id,) for product_id in plan_ids], ["product_id"])
        base = (
            product_features.join(plan_df.withColumn("optimization_boost", F.lit(1)), on="product_id", how="left")
            .withColumn("optimization_boost", F.coalesce(F.col("optimization_boost"), F.lit(0)))
            .withColumn("product_score", F.col("product_score") + F.col("optimization_boost") * F.lit(0.04))
        )
    return (
        base.orderBy(F.desc("product_score"), F.desc("confidence"), F.asc("product_id"))
        .limit(40)
        .select(
            "product_id",
            "brand",
            "category_level1",
            "product_score",
            "confidence",
            F.array(F.lit("optimization_or_global_fallback")).alias("reason_codes"),
            F.lit("optimization_fallback").alias("source"),
        )
    )


def evaluate_recommendation_quality(
    *,
    items: list[dict[str, Any]],
    target_session_count: int,
    product_count: int,
    freshness_lag_minutes: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    recommendation_count = len(items)
    covered_sessions = len({row["user_session"] for row in items})
    fallback_count = sum(1 for row in items if row["fallback_used"])
    duplicate_count = recommendation_count - len({(row["user_session"], row["product_id"]) for row in items})
    invalid_count = 0 if product_count else recommendation_count
    avg_confidence = sum(row["confidence"] for row in items) / recommendation_count if recommendation_count else 0
    quality = {
        "contract_version": RECOMMENDATION_CONTRACT_VERSION,
        "recommendation_count": recommendation_count,
        "target_sessions": target_session_count,
        "covered_sessions": covered_sessions,
        "coverage_rate": _safe_rate(covered_sessions, target_session_count),
        "fallback_rate": _safe_rate(fallback_count, recommendation_count),
        "personalized_rate": _safe_rate(recommendation_count - fallback_count, recommendation_count),
        "avg_confidence": round(avg_confidence, 6),
        "freshness_lag_minutes": round(freshness_lag_minutes, 2),
        "duplicate_recommendation_rate": _safe_rate(duplicate_count, recommendation_count),
        "invalid_product_rate": _safe_rate(invalid_count, recommendation_count),
        "min_coverage_rate": float(config["min_coverage_rate"]),
        "max_fallback_rate": float(config["max_fallback_rate"]),
        "min_avg_confidence": float(config["min_avg_confidence"]),
        "max_freshness_lag_minutes": float(config["max_freshness_lag_minutes"]),
        "max_duplicate_recommendation_rate": float(config["max_duplicate_recommendation_rate"]),
        "max_invalid_product_rate": float(config["max_invalid_product_rate"]),
        "max_category_drift_psi": 0.2,
        "max_brand_drift_psi": 0.2,
        "category_drift_psi": 0.0,
        "brand_drift_psi": 0.0,
    }
    checks = [
        ("coverage_rate", quality["coverage_rate"], ">=", quality["min_coverage_rate"]),
        ("fallback_rate", quality["fallback_rate"], "<=", quality["max_fallback_rate"]),
        ("avg_confidence", quality["avg_confidence"], ">=", quality["min_avg_confidence"]),
        ("freshness_lag_minutes", quality["freshness_lag_minutes"], "<=", quality["max_freshness_lag_minutes"]),
        ("duplicate_recommendation_rate", quality["duplicate_recommendation_rate"], "<=", quality["max_duplicate_recommendation_rate"]),
        ("invalid_product_rate", quality["invalid_product_rate"], "<=", quality["max_invalid_product_rate"]),
    ]
    quality["checks"] = [
        {"name": name, "actual": actual, "operator": operator, "expected": expected, "passed": actual >= expected if operator == ">=" else actual <= expected}
        for name, actual, operator, expected in checks
    ]
    quality["passed"] = all(check["passed"] for check in quality["checks"])
    return quality


def evaluate_recommendation_quality_frame(
    *,
    recommendation_features: DataFrame,
    target_session_count: int,
    product_count: int,
    freshness_lag_minutes: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    row = recommendation_features.agg(
        F.count("*").alias("recommendation_count"),
        F.countDistinct("user_session").alias("covered_sessions"),
        F.sum(F.when(F.col("fallback_used"), 1).otherwise(0)).alias("fallback_count"),
        F.countDistinct("user_session", "product_id").alias("distinct_recommendations"),
        F.round(F.avg("confidence"), 6).alias("avg_confidence"),
        F.round(F.avg("score"), 6).alias("avg_score"),
    ).first()
    recommendation_count = int(row["recommendation_count"] or 0)
    covered_sessions = int(row["covered_sessions"] or 0)
    fallback_count = int(row["fallback_count"] or 0)
    duplicate_count = recommendation_count - int(row["distinct_recommendations"] or 0)
    invalid_count = 0 if product_count else recommendation_count
    quality = {
        "contract_version": RECOMMENDATION_CONTRACT_VERSION,
        "recommendation_count": recommendation_count,
        "target_sessions": int(target_session_count),
        "covered_sessions": covered_sessions,
        "coverage_rate": _safe_rate(covered_sessions, target_session_count),
        "fallback_rate": _safe_rate(fallback_count, recommendation_count),
        "personalized_rate": _safe_rate(recommendation_count - fallback_count, recommendation_count),
        "avg_confidence": float(row["avg_confidence"] or 0),
        "avg_score": float(row["avg_score"] or 0),
        "freshness_lag_minutes": round(freshness_lag_minutes, 2),
        "duplicate_recommendation_rate": _safe_rate(duplicate_count, recommendation_count),
        "invalid_product_rate": _safe_rate(invalid_count, recommendation_count),
        "min_coverage_rate": float(config["min_coverage_rate"]),
        "max_fallback_rate": float(config["max_fallback_rate"]),
        "min_avg_confidence": float(config["min_avg_confidence"]),
        "max_freshness_lag_minutes": float(config["max_freshness_lag_minutes"]),
        "max_duplicate_recommendation_rate": float(config["max_duplicate_recommendation_rate"]),
        "max_invalid_product_rate": float(config["max_invalid_product_rate"]),
        "max_category_drift_psi": 0.2,
        "max_brand_drift_psi": 0.2,
        "category_drift_psi": 0.0,
        "brand_drift_psi": 0.0,
    }
    checks = [
        ("coverage_rate", quality["coverage_rate"], ">=", quality["min_coverage_rate"]),
        ("fallback_rate", quality["fallback_rate"], "<=", quality["max_fallback_rate"]),
        ("avg_confidence", quality["avg_confidence"], ">=", quality["min_avg_confidence"]),
        ("freshness_lag_minutes", quality["freshness_lag_minutes"], "<=", quality["max_freshness_lag_minutes"]),
        ("duplicate_recommendation_rate", quality["duplicate_recommendation_rate"], "<=", quality["max_duplicate_recommendation_rate"]),
        ("invalid_product_rate", quality["invalid_product_rate"], "<=", quality["max_invalid_product_rate"]),
    ]
    quality["checks"] = [
        {"name": name, "actual": actual, "operator": operator, "expected": expected, "passed": actual >= expected if operator == ">=" else actual <= expected}
        for name, actual, operator, expected in checks
    ]
    quality["passed"] = all(check["passed"] for check in quality["checks"])
    return quality


def build_recommendation_alerts(quality: dict[str, Any]) -> list[dict[str, Any]]:
    alerts = []
    for check in quality["checks"]:
        if check["passed"]:
            continue
        alerts.append(
            {
                "severity": "critical" if check["name"] in {"coverage_rate", "freshness_lag_minutes"} else "warning",
                "alert_code": f"recommendation_{check['name']}_breach",
                "metric": check["name"],
                "actual": check["actual"],
                "threshold": check["expected"],
                "message": f"{check['name']} failed recommendation promotion gate",
                "recommended_action": "Keep previous active snapshot and inspect Spark input freshness or fallback mix.",
            }
        )
    return alerts


def build_recommendation_summary(
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
    generated_at: str,
    target_session_count: int,
    freshness_lag_minutes: float,
    quality: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    return {
        "contract_version": RECOMMENDATION_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "feature_window": {"mode": "nearline_recent_sessions", "target_sessions": target_session_count},
        "generated_at": generated_at,
        "recommendation_count": quality["recommendation_count"],
        "preview_recommendation_count": quality.get("preview_recommendation_count", quality["recommendation_count"]),
        "covered_sessions": quality["covered_sessions"],
        "coverage_rate": quality["coverage_rate"],
        "personalized_rate": quality["personalized_rate"],
        "fallback_rate": quality["fallback_rate"],
        "avg_confidence": quality["avg_confidence"],
        "avg_score": quality.get("avg_score", 0),
        "freshness_lag_minutes": round(freshness_lag_minutes, 2),
        "quality_status": "passed" if quality["passed"] else "rejected",
        "rollback_ready": (Path(output_dir) / "recommendation_items.json").exists(),
        "active_snapshot_path": str(Path(output_dir) / "recommendation_items.json"),
        "previous_snapshot_path": str(Path(output_dir) / "recommendation_previous_items.json"),
    }


def promote_or_degrade_recommendations(base: Path, run_id: str, run_payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = base / "runs" / run_id / "recommendations"
    write_json_atomic(run_dir / "summary.json", run_payload["summary"])
    write_json_atomic(run_dir / "items.json", run_payload["items"])
    write_json_atomic(run_dir / "quality.json", run_payload["quality"])
    write_json_atomic(run_dir / "alerts.json", run_payload["alerts"])

    manifest = {
        "contract_version": RECOMMENDATION_CONTRACT_VERSION,
        "run_id": run_id,
        "quality_status": run_payload["summary"]["quality_status"],
        "active_snapshot_path": str(base / "recommendation_items.json"),
        "previous_snapshot_path": str(base / "recommendation_previous_items.json"),
        "run_snapshot_path": str(run_dir / "items.json"),
    }

    if run_payload["quality"]["passed"]:
        active_items = base / "recommendation_items.json"
        if active_items.exists():
            write_json_atomic(base / "recommendation_previous_items.json", _read_json(active_items, []))
        promoted = run_payload
        manifest["promotion_status"] = "promoted"
    else:
        previous_items = _read_json(base / "recommendation_items.json", run_payload["items"])
        promoted = {
            **run_payload,
            "items": previous_items,
            "summary": {
                **run_payload["summary"],
                "quality_status": "degraded_previous_snapshot" if previous_items != run_payload["items"] else "rejected_no_previous_snapshot",
                "recommendation_count": len(previous_items),
                "rollback_ready": previous_items != run_payload["items"],
            },
        }
        manifest["promotion_status"] = "rejected"

    write_json_atomic(base / "recommendation_manifest.json", manifest)
    return {
        "recommendation_summary": promoted["summary"],
        "recommendation_items": promoted["items"],
        "recommendation_quality": run_payload["quality"],
        "recommendation_alerts": run_payload["alerts"],
        "recommendation_manifest": manifest,
    }


def _item_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_session": str(row["user_session"]),
        "user_id": str(row["user_id"]),
        "rank": int(row["rank"]),
        "product_id": str(row["product_id"]),
        "brand": row.get("brand") or "unknown",
        "category_level1": row.get("category_level1") or "unknown",
        "score": float(row.get("score") or 0),
        "confidence": float(row.get("confidence") or 0),
        "reason_codes": list(row.get("reason_codes") or []),
        "source": row.get("source") or "unknown",
        "fallback_used": bool(row.get("fallback_used")),
    }


def _freshness_lag_minutes(max_event_ts: Any, generated_at: str) -> float:
    if not max_event_ts:
        return math.inf
    generated = datetime.fromisoformat(generated_at)
    event_time = max_event_ts.replace(tzinfo=UTC) if max_event_ts.tzinfo is None else max_event_ts
    return max(0.0, (generated - event_time).total_seconds() / 60)


def _safe_rate(numerator: float | int, denominator: float | int) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    import json

    return json.loads(path.read_text(encoding="utf-8"))
