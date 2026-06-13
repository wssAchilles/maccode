from __future__ import annotations

import math
from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


EXPERIMENT_CONTRACT_VERSION = "growth-experimentation/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 100,
    "treatment_split": 0.5,
    "min_treatment_users": 20,
    "min_control_users": 20,
    "max_segment_imbalance": 0.2,
    "min_assignment_users": 50,
    "srm_alpha": 0.001,
    "significance_alpha": 0.05,
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
    results = build_experiment_results(assignments, config, run_id=run_id)
    uplift = build_uplift_results(assignments, config, run_id=run_id)

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
        "experiment_results": results,
        "experiment_uplift": uplift,
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
        .withColumn(
            "uplift_score",
            F.round(
                F.col("expected_uplift_rate")
                + F.least(F.col("carts") / F.greatest(F.col("views"), F.lit(1)), F.lit(1.0)) * F.lit(0.02)
                + F.when(F.col("risk_band").isin("convert_intent", "at_risk"), F.lit(0.01)).otherwise(F.lit(0.0)),
                6,
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
            "expected_uplift_rate",
            "expected_incremental_purchase_prob",
            "expected_incremental_gmv",
            "uplift_score",
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


def build_experiment_results(assignments: DataFrame, config: dict[str, Any], *, run_id: str) -> list[dict[str, Any]]:
    aggregates = (
        assignments.groupBy("experiment_key", "name", "primary_metric", "variant")
        .agg(
            F.countDistinct("user_id").alias("users"),
            F.sum(F.when(F.col("purchases") > 0, 1).otherwise(0)).alias("conversions"),
            F.sum("purchases").alias("purchases"),
            F.sum("views").alias("views"),
            F.sum("carts").alias("carts"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.round(F.sum("expected_incremental_gmv"), 2).alias("expected_incremental_gmv"),
            F.round(F.avg("uplift_score"), 6).alias("avg_uplift_score"),
        )
        .collect()
    )
    by_experiment: dict[str, dict[str, Any]] = {}
    for row in aggregates:
        item = _json_safe(row.asDict())
        current = by_experiment.setdefault(
            str(item["experiment_key"]),
            {
                "experiment_key": str(item["experiment_key"]),
                "name": item.get("name") or str(item["experiment_key"]),
                "primary_metric": item.get("primary_metric") or "purchase_rate",
                "variants": {},
            },
        )
        current["variants"][str(item["variant"])] = item

    result_rows = []
    for experiment in sorted(by_experiment.values(), key=lambda row: row["experiment_key"]):
        treatment = experiment["variants"].get("treatment", {})
        control = experiment["variants"].get("control", {})
        treatment_users = int(treatment.get("users") or 0)
        control_users = int(control.get("users") or 0)
        total_users = treatment_users + control_users
        treatment_rate = _safe_rate(float(treatment.get("conversions") or 0), treatment_users)
        control_rate = _safe_rate(float(control.get("conversions") or 0), control_users)
        absolute_lift = round(treatment_rate - control_rate, 6)
        relative_lift = round(absolute_lift / control_rate, 6) if control_rate else None
        standard_error = _two_proportion_standard_error(treatment_rate, treatment_users, control_rate, control_users)
        p_value = _normal_two_sided_p_value(absolute_lift, standard_error) if standard_error else None
        ci_low = round(absolute_lift - 1.96 * standard_error, 6) if standard_error else None
        ci_high = round(absolute_lift + 1.96 * standard_error, 6) if standard_error else None
        srm = _srm_stats(treatment_users, control_users, float(config["treatment_split"]))
        srm_passed = srm["srm_p_value"] >= float(config["srm_alpha"])
        decision = _experiment_decision(
            total_users=total_users,
            srm_passed=srm_passed,
            p_value=p_value,
            absolute_lift=absolute_lift,
            config=config,
        )
        result_rows.append(
            {
                "contract_version": EXPERIMENT_CONTRACT_VERSION,
                "run_id": run_id,
                "experiment_key": experiment["experiment_key"],
                "name": experiment["name"],
                "primary_metric": experiment["primary_metric"],
                "measurement_status": "offline_history_replay",
                "oec_metric": "purchase_rate",
                "treatment_users": treatment_users,
                "control_users": control_users,
                "expected_treatment_ratio": float(config["treatment_split"]),
                "observed_treatment_ratio": _safe_rate(treatment_users, total_users),
                "srm_chi_square": srm["srm_chi_square"],
                "srm_p_value": srm["srm_p_value"],
                "srm_status": "passed" if srm_passed else "failed",
                "control_mean": control_rate,
                "treatment_mean": treatment_rate,
                "absolute_lift": absolute_lift,
                "relative_lift": relative_lift,
                "standard_error": round(standard_error, 6) if standard_error else None,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "p_value": p_value,
                "decision": decision,
                "variant_rows": [
                    _variant_result("treatment", treatment),
                    _variant_result("control", control),
                ],
                "causal_caveat": "offline_history_replay_not_causal",
            }
        )
    return result_rows


def build_uplift_results(assignments: DataFrame, config: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    ranked = assignments.withColumn(
        "uplift_decile",
        F.ntile(10).over(Window.partitionBy("experiment_key").orderBy(F.desc("uplift_score"), F.asc("user_id"))),
    )
    rows = (
        ranked.groupBy("experiment_key", "uplift_decile", "variant")
        .agg(
            F.countDistinct("user_id").alias("users"),
            F.sum(F.when(F.col("purchases") > 0, 1).otherwise(0)).alias("conversions"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
            F.round(F.avg("uplift_score"), 6).alias("avg_uplift_score"),
        )
        .collect()
    )
    by_decile: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        item = _json_safe(row.asDict())
        key = (str(item["experiment_key"]), int(item["uplift_decile"]))
        current = by_decile.setdefault(
            key,
            {"experiment_key": key[0], "decile": key[1], "variants": {}},
        )
        current["variants"][str(item["variant"])] = item

    deciles = []
    cumulative_gain: dict[str, float] = {}
    auuc_by_experiment: dict[str, float] = {}
    for (experiment_key, decile), item in sorted(by_decile.items()):
        treatment = item["variants"].get("treatment", {})
        control = item["variants"].get("control", {})
        treatment_users = int(treatment.get("users") or 0)
        control_users = int(control.get("users") or 0)
        treatment_rate = _safe_rate(float(treatment.get("conversions") or 0), treatment_users)
        control_rate = _safe_rate(float(control.get("conversions") or 0), control_users)
        uplift = round(treatment_rate - control_rate, 6)
        gain = uplift * max(treatment_users, 1)
        cumulative_gain[experiment_key] = round(cumulative_gain.get(experiment_key, 0.0) + gain, 6)
        auuc_by_experiment[experiment_key] = round(auuc_by_experiment.get(experiment_key, 0.0) + cumulative_gain[experiment_key], 6)
        deciles.append(
            {
                "experiment_key": experiment_key,
                "decile": decile,
                "treatment_users": treatment_users,
                "control_users": control_users,
                "treatment_conversion_rate": treatment_rate,
                "control_conversion_rate": control_rate,
                "uplift": uplift,
                "cumulative_gain": cumulative_gain[experiment_key],
                "avg_uplift_score": round(
                    max(float(treatment.get("avg_uplift_score") or 0), float(control.get("avg_uplift_score") or 0)),
                    6,
                ),
            }
        )
    return {
        "contract_version": EXPERIMENT_CONTRACT_VERSION,
        "run_id": run_id,
        "measurement_status": "offline_history_replay",
        "causal_valid": False,
        "causal_caveat": "randomized_exposure_and_outcome_required_for_true_uplift",
        "summary": [
            {
                "experiment_key": experiment_key,
                "auuc": round(auuc, 6),
                "qini_auc": round(auuc, 6),
                "decile_count": sum(1 for row in deciles if row["experiment_key"] == experiment_key),
            }
            for experiment_key, auuc in sorted(auuc_by_experiment.items())
        ],
        "deciles": deciles,
        "quality_gates": [
            {
                "name": "causal_outcome_available",
                "actual": "offline_history_replay",
                "operator": "==",
                "expected": "randomized_experiment_results",
                "passed": False,
            }
        ],
    }


def _variant_result(variant: str, row: dict[str, Any]) -> dict[str, Any]:
    users = int(row.get("users") or 0)
    conversions = int(row.get("conversions") or 0)
    return {
        "variant": variant,
        "users": users,
        "conversions": conversions,
        "conversion_rate": _safe_rate(conversions, users),
        "purchases": int(row.get("purchases") or 0),
        "views": int(row.get("views") or 0),
        "carts": int(row.get("carts") or 0),
        "revenue": float(row.get("revenue") or 0),
        "expected_incremental_gmv": float(row.get("expected_incremental_gmv") or 0),
        "avg_uplift_score": float(row.get("avg_uplift_score") or 0),
    }


def _srm_stats(treatment_users: int, control_users: int, treatment_split: float) -> dict[str, float]:
    total = treatment_users + control_users
    if not total:
        return {"srm_chi_square": 0.0, "srm_p_value": 1.0}
    expected_treatment = total * treatment_split
    expected_control = total * (1.0 - treatment_split)
    chi_square = 0.0
    if expected_treatment:
        chi_square += ((treatment_users - expected_treatment) ** 2) / expected_treatment
    if expected_control:
        chi_square += ((control_users - expected_control) ** 2) / expected_control
    return {"srm_chi_square": round(chi_square, 6), "srm_p_value": round(math.erfc(math.sqrt(chi_square / 2)), 6)}


def _two_proportion_standard_error(treatment_rate: float, treatment_users: int, control_rate: float, control_users: int) -> float:
    if treatment_users <= 0 or control_users <= 0:
        return 0.0
    return math.sqrt((treatment_rate * (1 - treatment_rate) / treatment_users) + (control_rate * (1 - control_rate) / control_users))


def _normal_two_sided_p_value(effect: float, standard_error: float) -> float | None:
    if standard_error <= 0:
        return None
    return round(math.erfc(abs(effect / standard_error) / math.sqrt(2)), 6)


def _experiment_decision(
    *,
    total_users: int,
    srm_passed: bool,
    p_value: float | None,
    absolute_lift: float,
    config: dict[str, Any],
) -> str:
    if total_users < int(config["min_assignment_users"]):
        return "needs_more_sample"
    if not srm_passed:
        return "blocked_by_srm"
    if p_value is None:
        return "not_measurable"
    if p_value <= float(config["significance_alpha"]) and absolute_lift > 0:
        return "positive_significant"
    if p_value <= float(config["significance_alpha"]) and absolute_lift < 0:
        return "negative_significant"
    return "not_significant"


def _safe_rate(numerator: float | int, denominator: float | int) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
