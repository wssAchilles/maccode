from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


EXPERIMENT_CONTRACT_VERSION = "growth-experimentation/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "treatment_split": 0.5,
    "min_treatment_users": 20,
    "min_control_users": 20,
    "max_segment_imbalance": 0.2,
    "min_assignment_users": 50,
}


def experiment_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_experiment_outputs(
    user_lifecycle: DataFrame,
    recommendation_features: DataFrame,
    optimization_plan: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    run_id: str,
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    experiments = build_experiment_catalog(optimization_plan)
    preview_limit = int(config["preview_limit"])
    assignments = build_assignments(user_lifecycle, experiments, float(config["treatment_split"]), run_id).persist(StorageLevel.MEMORY_AND_DISK)
    segment_readiness = build_segment_readiness(assignments).persist(StorageLevel.MEMORY_AND_DISK)
    recommendation_coverage = build_recommendation_coverage(recommendation_features)
    assignment_preview = collect_assignments(assignments, preview_limit)
    segment_preview = collect_segments(segment_readiness, preview_limit)
    summary = build_summary(assignments, segment_readiness, experiments, recommendation_coverage, optimization_plan, config, run_id)
    guardrails = build_guardrails(summary, segment_preview, recommendation_coverage, config)
    catalog = build_catalog_payload(experiments, recommendation_coverage)

    frames = {
        "experiment_assignments": assignments,
        "experiment_segment_readiness": segment_readiness,
    }
    metrics = {
        "experiment_summary": {**summary, "guardrail_status": guardrails["status"]},
        "experiment_catalog": catalog,
        "experiment_assignments": assignment_preview,
        "experiment_segments": segment_preview,
        "experiment_guardrails": guardrails,
    }
    return frames, metrics


def build_experiment_catalog(optimization_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_categories = sorted(
        {str(row.get("category_level1") or "unknown") for row in optimization_plan if row.get("category_level1")}
    )
    return [
        {
            "experiment_key": "lifecycle_reactivation",
            "name": "生命周期再激活策略",
            "primary_metric": "purchase_rate",
            "secondary_metric": "revenue_per_user",
            "target_rule": "risk_band in convert_intent or at_risk",
            "policy": "category-personalized recovery and incentive message",
            "expected_uplift_rate": 0.035,
            "status": "ready",
        },
        {
            "experiment_key": "recommendation_personalization",
            "name": "推荐个性化策略",
            "primary_metric": "view_to_cart_rate",
            "secondary_metric": "recommendation_coverage",
            "target_rule": "all active lifecycle users",
            "policy": "personalized top-k recommendation over global fallback",
            "expected_uplift_rate": 0.018,
            "status": "ready",
        },
        {
            "experiment_key": "merchandising_boost",
            "name": "商品运营位策略",
            "primary_metric": "incremental_gmv",
            "secondary_metric": "risk_adjusted_purchase_rate",
            "target_rule": f"preferred category in selected categories: {', '.join(selected_categories[:6]) or 'pending'}",
            "policy": "optimization-selected product exposure with budget guardrails",
            "expected_uplift_rate": 0.025,
            "status": "ready" if optimization_plan else "waiting_for_optimization_plan",
        },
    ]


def build_assignments(user_lifecycle: DataFrame, experiments: list[dict[str, Any]], treatment_split: float, run_id: str) -> DataFrame:
    spark = user_lifecycle.sparkSession
    experiment_df = spark.createDataFrame(experiments)
    base = user_lifecycle.crossJoin(experiment_df)
    hash_bucket = F.pmod(F.abs(F.hash(F.col("user_id"), F.col("experiment_key"))), F.lit(10_000)) / F.lit(10_000.0)
    return (
        base.withColumn(
            "eligible",
            F.when(
                (F.col("experiment_key") == "lifecycle_reactivation")
                & F.col("risk_band").isin("convert_intent", "at_risk"),
                F.lit(True),
            )
            .when(F.col("experiment_key") == "recommendation_personalization", F.lit(True))
            .when(
                (F.col("experiment_key") == "merchandising_boost")
                & F.col("lifecycle_segment").isin("champion", "high_value", "buyer", "cart_intent"),
                F.lit(True),
            )
            .otherwise(F.lit(False)),
        )
        .filter(F.col("eligible"))
        .withColumn("assignment_bucket", F.round(hash_bucket, 6))
        .withColumn("variant", F.when(F.col("assignment_bucket") < treatment_split, F.lit("treatment")).otherwise(F.lit("control")))
        .withColumn(
            "expected_incremental_purchase_prob",
            F.round(
                F.when(F.col("variant") == "treatment", F.col("expected_uplift_rate")).otherwise(F.lit(0.0)),
                6,
            ),
        )
        .withColumn(
            "expected_incremental_gmv",
            F.round(
                F.when(
                    F.col("variant") == "treatment",
                    F.col("expected_uplift_rate") * F.greatest(F.coalesce(F.col("avg_order_value"), F.lit(0.0)), F.lit(50.0)),
                ).otherwise(F.lit(0.0)),
                2,
            ),
        )
        .withColumn("source_run_id", F.lit(run_id))
        .withColumn("contract_version", F.lit(EXPERIMENT_CONTRACT_VERSION))
        .select(
            "contract_version",
            "source_run_id",
            "experiment_key",
            "name",
            "user_id",
            "variant",
            "assignment_bucket",
            "lifecycle_segment",
            "risk_band",
            "preferred_category_level1",
            "sessions",
            "views",
            "carts",
            "purchases",
            "revenue",
            "expected_incremental_purchase_prob",
            "expected_incremental_gmv",
            "policy",
            "primary_metric",
        )
    )


def build_segment_readiness(assignments: DataFrame) -> DataFrame:
    totals = assignments.groupBy("experiment_key").agg(F.countDistinct("user_id").alias("experiment_users"))
    by_segment = (
        assignments.groupBy("experiment_key", "lifecycle_segment", "variant")
        .agg(
            F.countDistinct("user_id").alias("users"),
            F.round(F.sum("revenue"), 2).alias("observed_revenue"),
            F.sum("purchases").alias("observed_purchases"),
            F.round(F.sum("expected_incremental_gmv"), 2).alias("expected_incremental_gmv"),
        )
        .join(totals, on="experiment_key", how="left")
        .withColumn("segment_share", F.round(F.col("users") / F.col("experiment_users"), 6))
        .orderBy("experiment_key", "lifecycle_segment", "variant")
    )
    return by_segment


def build_recommendation_coverage(recommendation_features: DataFrame) -> dict[str, Any]:
    row = recommendation_features.agg(
        F.count("*").alias("recommendations"),
        F.countDistinct("user_session").alias("covered_sessions"),
        F.sum(F.when(F.col("fallback_used"), 1).otherwise(0)).alias("fallback_items"),
        F.round(F.avg("confidence"), 6).alias("avg_confidence"),
    ).first()
    recommendations = int(row["recommendations"] or 0)
    fallback_items = int(row["fallback_items"] or 0)
    return {
        "recommendations": recommendations,
        "covered_sessions": int(row["covered_sessions"] or 0),
        "fallback_items": fallback_items,
        "fallback_rate": round(fallback_items / recommendations, 6) if recommendations else 0.0,
        "avg_confidence": float(row["avg_confidence"] or 0.0),
    }


def collect_assignments(assignments: DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = (
        assignments.orderBy("experiment_key", F.desc("expected_incremental_gmv"), "variant", "user_id")
        .limit(limit)
        .collect()
    )
    return [_json_safe(row.asDict()) for row in rows]


def collect_segments(segment_readiness: DataFrame, limit: int) -> list[dict[str, Any]]:
    return [_json_safe(row.asDict()) for row in segment_readiness.limit(limit).collect()]


def build_summary(
    assignments: DataFrame,
    segment_readiness: DataFrame,
    experiments: list[dict[str, Any]],
    recommendation_coverage: dict[str, Any],
    optimization_plan: list[dict[str, Any]],
    config: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    row = assignments.agg(
        F.count("*").alias("assignment_rows"),
        F.countDistinct("user_id").alias("assigned_users"),
        F.sum(F.when(F.col("variant") == "treatment", 1).otherwise(0)).alias("treatment_assignments"),
        F.sum(F.when(F.col("variant") == "control", 1).otherwise(0)).alias("control_assignments"),
        F.round(F.sum("expected_incremental_gmv"), 2).alias("expected_incremental_gmv"),
        F.round(F.sum("expected_incremental_purchase_prob"), 6).alias("expected_incremental_purchases"),
    ).first()
    experiment_rows = (
        assignments.groupBy("experiment_key", "name")
        .agg(
            F.countDistinct("user_id").alias("assigned_users"),
            F.sum(F.when(F.col("variant") == "treatment", 1).otherwise(0)).alias("treatment_users"),
            F.sum(F.when(F.col("variant") == "control", 1).otherwise(0)).alias("control_users"),
            F.round(F.sum("expected_incremental_gmv"), 2).alias("expected_incremental_gmv"),
        )
        .orderBy("experiment_key")
        .collect()
    )
    return {
        "contract_version": EXPERIMENT_CONTRACT_VERSION,
        "run_id": run_id,
        "experiment_count": len(experiments),
        "assignment_rows": int(row["assignment_rows"] or 0),
        "assigned_users": int(row["assigned_users"] or 0),
        "treatment_assignments": int(row["treatment_assignments"] or 0),
        "control_assignments": int(row["control_assignments"] or 0),
        "treatment_split": float(config["treatment_split"]),
        "expected_incremental_gmv": float(row["expected_incremental_gmv"] or 0),
        "expected_incremental_purchases": float(row["expected_incremental_purchases"] or 0),
        "recommendation_coverage": recommendation_coverage,
        "optimization_selected_count": len(optimization_plan),
        "experiments": [_json_safe(item.asDict()) for item in experiment_rows],
        "causal_caveat": "Offline estimates are planning priors only; production lift requires randomized holdout measurement.",
        "segment_rows": segment_readiness.count(),
    }


def build_guardrails(
    summary: dict[str, Any],
    segments: list[dict[str, Any]],
    recommendation_coverage: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    min_treatment = int(config["min_treatment_users"])
    min_control = int(config["min_control_users"])
    min_assignment_users = int(config["min_assignment_users"])
    max_imbalance = float(config["max_segment_imbalance"])
    checks = [
        {
            "name": "min_assignment_users",
            "actual": summary["assigned_users"],
            "operator": ">=",
            "expected": min_assignment_users,
            "passed": summary["assigned_users"] >= min_assignment_users,
        },
        {
            "name": "min_treatment_assignments",
            "actual": summary["treatment_assignments"],
            "operator": ">=",
            "expected": min_treatment,
            "passed": summary["treatment_assignments"] >= min_treatment,
        },
        {
            "name": "min_control_assignments",
            "actual": summary["control_assignments"],
            "operator": ">=",
            "expected": min_control,
            "passed": summary["control_assignments"] >= min_control,
        },
        {
            "name": "recommendation_avg_confidence",
            "actual": recommendation_coverage["avg_confidence"],
            "operator": ">=",
            "expected": 0.01,
            "passed": recommendation_coverage["avg_confidence"] >= 0.01,
        },
    ]
    imbalance_rows = build_segment_imbalance(segments)
    max_actual_imbalance = max((row["imbalance"] for row in imbalance_rows), default=0.0)
    checks.append(
        {
            "name": "max_segment_variant_imbalance",
            "actual": max_actual_imbalance,
            "operator": "<=",
            "expected": max_imbalance,
            "passed": max_actual_imbalance <= max_imbalance,
        }
    )
    return {
        "contract_version": EXPERIMENT_CONTRACT_VERSION,
        "status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "checks": checks,
        "segment_imbalance": imbalance_rows,
        "recommended_action": "Launch only experiments with sufficient treatment/control balance; keep holdout immutable during measurement.",
    }


def build_segment_imbalance(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], dict[str, int]] = {}
    for row in segments:
        key = (str(row["experiment_key"]), str(row["lifecycle_segment"]))
        totals.setdefault(key, {"treatment": 0, "control": 0})
        totals[key][str(row["variant"])] = int(row["users"] or 0)
    result = []
    for (experiment_key, lifecycle_segment), variants in sorted(totals.items()):
        treatment = variants.get("treatment", 0)
        control = variants.get("control", 0)
        total = treatment + control
        imbalance = round(abs(treatment - control) / total, 6) if total else 0.0
        result.append(
            {
                "experiment_key": experiment_key,
                "lifecycle_segment": lifecycle_segment,
                "treatment_users": treatment,
                "control_users": control,
                "imbalance": imbalance,
            }
        )
    return result


def build_catalog_payload(experiments: list[dict[str, Any]], recommendation_coverage: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **experiment,
            "contract_version": EXPERIMENT_CONTRACT_VERSION,
            "measurement_window": "7-14 days after exposure",
            "guardrail_metrics": ["variant balance", "recommendation coverage", "fallback pressure", "quality gate status"],
            "recommendation_coverage": recommendation_coverage if experiment["experiment_key"] == "recommendation_personalization" else None,
        }
        for experiment in experiments
    ]


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
