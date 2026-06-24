from __future__ import annotations

import argparse
import hashlib
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.aggregations import build_metrics
from spark_jobs.affinity import AFFINITY_CONTRACT_VERSION, affinity_config, build_affinity_outputs
from spark_jobs.anomaly import ANOMALY_CONTRACT_VERSION, anomaly_config, build_anomaly_outputs
from spark_jobs.attribution import ATTRIBUTION_CONTRACT_VERSION, attribution_config, build_attribution_outputs
from spark_jobs.cleaning import build_quality_report, clean_events, evaluate_quality
from spark_jobs.cohort import COHORT_CONTRACT_VERSION, build_cohort_outputs, cohort_config
from spark_jobs.cart_recovery import (
    CART_RECOVERY_CONTRACT_VERSION,
    build_cart_recovery_outputs,
    cart_recovery_config,
)
from spark_jobs.dashboard_cube import build_dashboard_cube_outputs
from spark_jobs.dashboard_semantics import DASHBOARD_CUBE_CONTRACT_VERSION, DASHBOARD_SEMANTIC_VERSION
from spark_jobs.conversion import (
    CONVERSION_CONTRACT_VERSION,
    build_conversion_metrics,
    build_conversion_quality,
    build_session_facts,
)
from spark_jobs.feature_mart import (
    FEATURE_MART_CONTRACT_VERSION,
    build_feature_mart_outputs,
    feature_mart_config,
)
from spark_jobs.forecasting import (
    FORECAST_CONTRACT_VERSION,
    build_forecasting_outputs,
    forecasting_config,
)
from spark_jobs.experimentation import (
    EXPERIMENT_CONTRACT_VERSION,
    build_experiment_outputs,
    experiment_config,
)
from spark_jobs.journey import JOURNEY_CONTRACT_VERSION, build_journey_outputs, journey_config
from spark_jobs.lifecycle import LIFECYCLE_CONTRACT_VERSION, build_lifecycle_outputs, lifecycle_config
from spark_jobs.optimization import (
    OPTIMIZATION_CONTRACT_VERSION,
    build_optimization_candidates,
    build_optimization_outputs,
    optimization_config,
    solve_merchandising_plan,
)
from spark_jobs.portfolio import PORTFOLIO_CONTRACT_VERSION, build_portfolio_outputs, portfolio_config
from spark_jobs.recommendation import (
    RECOMMENDATION_CONTRACT_VERSION,
    build_recommendation_outputs,
    recommendation_config,
)
from spark_jobs.readers import read_events
from spark_jobs.session import build_spark
from spark_jobs.writers import write_json_atomic, write_metric_files
from spark_jobs.decision_maker import build_decision_manifest


CONTRACT_VERSION = "pipeline-run-governance/v1"
MAX_INPUT_FILE_SAMPLES = 20
TABLE_EVENT_COLUMNS = [
    "event_time",
    "event_type",
    "product_id",
    "category_id",
    "category_code",
    "category_level1",
    "brand",
    "price",
    "user_id",
    "user_session",
]


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_input_path(config: dict[str, Any]) -> str:
    data_config = config.get("data", {})
    storage_config = config.get("storage", {})
    input_path = data_config["input_path"]
    mode = storage_config.get("mode", "local")

    if mode == "auto" and str(input_path).startswith("hdfs://"):
        fallback = storage_config.get("local_fallback_input_path")
        if fallback:
            print(f"Storage mode auto: using local fallback path because no HDFS probe is configured: {fallback}")
            return fallback

    return input_path


def config_hash(config: dict[str, Any]) -> str:
    payload = yaml.safe_dump(config, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_input_snapshot(
    *,
    configured_input_path: str,
    actual_input_path: str,
    input_format: str,
    storage_mode: str,
    input_files: list[str],
) -> dict[str, Any]:
    files = sorted(input_files)
    sample_files = files[:MAX_INPUT_FILE_SAMPLES]
    return {
        "configured_input_path": configured_input_path,
        "actual_input_path": actual_input_path,
        "input_format": input_format,
        "storage_mode": storage_mode,
        "file_count": len(files),
        "files": sample_files,
        "file_sample_limit": MAX_INPUT_FILE_SAMPLES,
        "omitted_file_count": max(0, len(files) - len(sample_files)),
        "files_hash": hashlib.sha256("\n".join(files).encode("utf-8")).hexdigest() if files else None,
    }


def run_job(config: dict[str, Any], run_id: str | None = None) -> dict[str, object]:
    run_id = run_id or uuid4().hex
    started = time.perf_counter()
    spark_config = config.get("spark", {})
    data_config = config.get("data", {})
    quality_config = config.get("quality", {})
    feature_mart_settings = feature_mart_config(config.get("feature_mart"))
    affinity_settings = affinity_config(config.get("affinity"))
    attribution_settings = attribution_config(config.get("attribution"))
    cohort_settings = cohort_config(config.get("cohort"))
    cart_recovery_settings = cart_recovery_config(config.get("cart_recovery"))
    portfolio_settings = portfolio_config(config.get("portfolio"))
    forecasting_settings = forecasting_config(config.get("forecasting"))
    journey_settings = journey_config(config.get("journey"))
    anomaly_settings = anomaly_config(config.get("anomaly"))
    lifecycle_settings = lifecycle_config(config.get("lifecycle"))
    experiment_settings = experiment_config(config.get("experimentation"))
    optimization_settings = optimization_config(config.get("optimization"))
    recommendation_settings = recommendation_config(config.get("recommendation"))
    output_dir = data_config.get("output_dir", "data/cache")

    spark = build_spark(
        app_name=config.get("app", {}).get("name", "ecommerce-behavior-dashboard"),
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
        input_snapshot = build_input_snapshot(
            configured_input_path=data_config["input_path"],
            actual_input_path=actual_input_path,
            input_format=data_config.get("input_format", "csv"),
            storage_mode=config.get("storage", {}).get("mode", "local"),
            input_files=source_df.inputFiles(),
        )
        raw_df = source_df

        if data_config.get("limit"):
            raw_df = source_df.limit(int(data_config["limit"]))

        cleaned_df = clean_events(raw_df).persist(StorageLevel.MEMORY_AND_DISK)
        session_facts = build_session_facts(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
        quality = {
            **build_quality_report(raw_df, cleaned_df),
            **build_conversion_quality(raw_df, session_facts),
        }
        quality_gate = evaluate_quality(quality, quality_config.get("thresholds"))
        feature_mart_frames, feature_mart_metrics = build_feature_mart_outputs(
            raw_df,
            cleaned_df,
            feature_mart_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        top_n = int(data_config.get("top_n", 10))
        metrics = {
            **build_metrics(cleaned_df, quality, top_n),
            **build_conversion_metrics(cleaned_df, session_facts, top_n),
            **feature_mart_metrics,
        }
        dashboard_cube_frames, dashboard_cube_metrics = build_dashboard_cube_outputs(
            cleaned_df,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(dashboard_cube_metrics)
        affinity_frames, affinity_metrics = build_affinity_outputs(
            cleaned_df,
            affinity_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(affinity_metrics)
        attribution_frames, attribution_metrics = build_attribution_outputs(
            cleaned_df,
            attribution_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(attribution_metrics)
        cohort_frames, cohort_metrics = build_cohort_outputs(
            cleaned_df,
            cohort_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(cohort_metrics)
        cart_recovery_frames, cart_recovery_metrics = build_cart_recovery_outputs(
            cleaned_df,
            cart_recovery_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(cart_recovery_metrics)
        portfolio_frames, portfolio_metrics = build_portfolio_outputs(
            cleaned_df,
            portfolio_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(portfolio_metrics)
        forecast_frames, forecast_metrics = build_forecasting_outputs(
            cleaned_df,
            forecasting_settings,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(forecast_metrics)
        journey_frames, journey_metrics = build_journey_outputs(
            cleaned_df,
            journey_settings,
            run_id=run_id,
        )
        metrics.update(journey_metrics)
        anomaly_frames, anomaly_metrics = build_anomaly_outputs(
            feature_mart_frames["daily_category_behavior"],
            feature_mart_frames["daily_product_behavior"],
            feature_mart_metrics["feature_mart_quality"],
            feature_mart_metrics["feature_mart_freshness"],
            anomaly_settings,
            run_id=run_id,
            forecasting_backtest=metrics.get("forecasting_backtest", []),
            forecasting_series=metrics.get("forecasting_series", []),
        )
        metrics.update(anomaly_metrics)
        lifecycle_frames, lifecycle_metrics = build_lifecycle_outputs(
            feature_mart_frames["daily_user_behavior"],
            feature_mart_frames["daily_category_behavior"],
            lifecycle_settings,
            run_id=run_id,
        )
        metrics.update(lifecycle_metrics)
        candidates_df, optimization_candidates = build_optimization_candidates(
            cleaned_df,
            candidate_limit=int(optimization_settings["candidate_limit"]),
            global_purchase_rate=float(metrics["session_funnel"]["totals"]["view_to_purchase_rate"]),
        )
        optimization_result = solve_merchandising_plan(optimization_candidates, optimization_settings)
        optimization_metrics = build_optimization_outputs(
            optimization_candidates,
            optimization_result,
            optimization_settings,
        )
        metrics.update(optimization_metrics)
        recommendation_features, recommendation_metrics = build_recommendation_outputs(
            cleaned_df,
            optimization_result.selected,
            recommendation_settings,
            output_dir=output_dir,
            run_id=run_id,
            input_snapshot=input_snapshot,
        )
        metrics.update(recommendation_metrics)
        experiment_frames, experiment_metrics = build_experiment_outputs(
            lifecycle_frames["user_lifecycle"],
            recommendation_features,
            optimization_result.selected,
            experiment_settings,
            run_id=run_id,
        )
        metrics.update(experiment_metrics)
        decision_metrics = build_decision_manifest(
            anomaly_alerts=metrics.get("anomaly_alerts", []),
            optimization_plan=metrics.get("optimization_plan", []),
            forecasting_entities=metrics.get("forecasting_entities", []),
            run_id=run_id,
        )
        metrics["decision_manifest"] = decision_metrics
        _unpersist_frames(
            feature_mart_frames,
            affinity_frames,
            attribution_frames,
            cohort_frames,
            cart_recovery_frames,
            portfolio_frames,
            forecast_frames,
            journey_frames,
            anomaly_frames,
            lifecycle_frames,
            experiment_frames,
            candidates_df,
            recommendation_features,
            cleaned_df,
            session_facts,
        )
        elapsed_seconds = round(time.perf_counter() - started, 3)
        spark_application_id = spark.sparkContext.applicationId
        cleaned_rows_per_second = round(float(quality.get("cleaned_rows") or 0) / elapsed_seconds, 3) if elapsed_seconds else 0.0
        output_artifact_row_counts = {
            "cleaned_rows": int(quality.get("cleaned_rows") or 0),
            "session_fact_rows": int(quality.get("session_fact_rows") or 0),
            "recommendation_count": int(recommendation_metrics["recommendation_summary"].get("recommendation_count") or 0),
            "affinity_pair_base_rows": int(affinity_metrics["affinity_quality"].get("pair_base_rows") or 0),
            "experiment_assignment_rows": int(experiment_metrics["experiment_summary"].get("assignment_rows") or 0),
            "anomaly_signal_count": int(anomaly_metrics["anomaly_summary"].get("signal_count") or 0),
            "dashboard_cube_rows": int(metrics["dashboard_cube_summary"].get("cube_row_count") or 0),
        }
        processed_base = str(data_config.get("processed_dir", "data/processed/ecommerce_behavior"))
        output_artifacts = {
            "metrics_dir": output_dir,
            "table_events": str(Path(output_dir) / "table_events"),
            "decision_artifacts": {
                "manifest": str(Path(output_dir) / "decision_manifest.json"),
            },
            "dashboard_cube_artifacts": {
                "summary": str(Path(output_dir) / "dashboard_cube_summary.json"),
                "semantic_metrics": str(Path(output_dir) / "dashboard_semantic_metrics.json"),
                "total": str(Path(output_dir) / "dashboard_cube_total"),
                "daily": str(Path(output_dir) / "dashboard_cube_daily"),
                "base_dir": _child_path(processed_base, "dashboard_cube"),
            },
            "processed_dir": data_config.get("processed_dir"),
            "processed_events": _child_path(processed_base, "events"),
            "manifest_path": str(Path(output_dir) / "run_manifest.json"),
            "run_manifest_path": str(Path(output_dir) / "runs" / run_id / "manifest.json"),
            "conversion_artifacts": {
                "session_funnel": str(Path(output_dir) / "session_funnel.json"),
                "conversion_segments": str(Path(output_dir) / "conversion_segments.json"),
                "product_conversion": str(Path(output_dir) / "product_conversion.json"),
                "session_facts": _child_path(processed_base, "session_facts"),
            },
            "forecasting_artifacts": {
                "summary": str(Path(output_dir) / "forecasting_summary.json"),
                "series": str(Path(output_dir) / "forecasting_series.json"),
                "entities": str(Path(output_dir) / "forecasting_entities.json"),
                "backtest": str(Path(output_dir) / "forecasting_backtest.json"),
                "evaluation": str(Path(output_dir) / "forecasting_evaluation.json"),
                "risks": str(Path(output_dir) / "forecasting_risks.json"),
                "quality": str(Path(output_dir) / "forecasting_quality.json"),
                "base_dir": _child_path(processed_base, "forecasting"),
            },
            "affinity_artifacts": {
                "summary": str(Path(output_dir) / "affinity_summary.json"),
                "nodes": str(Path(output_dir) / "affinity_nodes.json"),
                "edges": str(Path(output_dir) / "affinity_edges.json"),
                "communities": str(Path(output_dir) / "affinity_communities.json"),
                "opportunities": str(Path(output_dir) / "affinity_opportunities.json"),
                "centrality": str(Path(output_dir) / "affinity_centrality.json"),
                "quality": str(Path(output_dir) / "affinity_quality.json"),
                "base_dir": _child_path(processed_base, "affinity"),
            },
            "attribution_artifacts": {
                "summary": str(Path(output_dir) / "attribution_summary.json"),
                "models": str(Path(output_dir) / "attribution_models.json"),
                "entities": str(Path(output_dir) / "attribution_entities.json"),
                "paths": str(Path(output_dir) / "attribution_paths.json"),
                "assists": str(Path(output_dir) / "attribution_assists.json"),
                "quality": str(Path(output_dir) / "attribution_quality.json"),
                "base_dir": _child_path(processed_base, "attribution"),
            },
            "cohort_artifacts": {
                "summary": str(Path(output_dir) / "cohort_summary.json"),
                "retention_matrix": str(Path(output_dir) / "cohort_retention_matrix.json"),
                "repurchase_intervals": str(Path(output_dir) / "cohort_repurchase_intervals.json"),
                "value_curves": str(Path(output_dir) / "cohort_value_curves.json"),
                "segments": str(Path(output_dir) / "cohort_segments.json"),
                "quality": str(Path(output_dir) / "cohort_quality.json"),
                "base_dir": _child_path(processed_base, "cohort_retention"),
            },
            "portfolio_artifacts": {
                "summary": str(Path(output_dir) / "portfolio_summary.json"),
                "categories": str(Path(output_dir) / "portfolio_category_mix.json"),
                "brands": str(Path(output_dir) / "portfolio_brand_mix.json"),
                "price_bands": str(Path(output_dir) / "portfolio_price_bands.json"),
                "product_concentration": str(Path(output_dir) / "portfolio_product_concentration.json"),
                "opportunities": str(Path(output_dir) / "portfolio_opportunities.json"),
                "quality": str(Path(output_dir) / "portfolio_quality.json"),
                "base_dir": _child_path(processed_base, "portfolio"),
            },
            "cart_recovery_artifacts": {
                "summary": str(Path(output_dir) / "cart_summary.json"),
                "categories": str(Path(output_dir) / "cart_category_segments.json"),
                "products": str(Path(output_dir) / "cart_product_segments.json"),
                "queue": str(Path(output_dir) / "cart_recovery_queue.json"),
                "quality": str(Path(output_dir) / "cart_quality.json"),
                "base_dir": _child_path(processed_base, "cart_recovery"),
            },
            "journey_artifacts": {
                "summary": str(Path(output_dir) / "journey_summary.json"),
                "paths": str(Path(output_dir) / "journey_paths.json"),
                "transitions": str(Path(output_dir) / "journey_transitions.json"),
                "exit_events": str(Path(output_dir) / "journey_exit_events.json"),
                "purchase_paths": str(Path(output_dir) / "journey_purchase_paths.json"),
                "base_dir": _child_path(processed_base, "journey"),
            },
            "optimization_artifacts": {
                "summary": str(Path(output_dir) / "optimization_summary.json"),
                "plan": str(Path(output_dir) / "optimization_plan.json"),
                "candidates": str(Path(output_dir) / "optimization_candidates.json"),
                "quality": str(Path(output_dir) / "optimization_quality.json"),
                "candidates_parquet": _child_path(processed_base, "optimization_candidates"),
            },
            "recommendation_artifacts": {
                "summary": str(Path(output_dir) / "recommendation_summary.json"),
                "items": str(Path(output_dir) / "recommendation_items.json"),
                "candidates": str(Path(output_dir) / "recommendation_candidates.json"),
                "quality": str(Path(output_dir) / "recommendation_quality.json"),
                "evaluation": str(Path(output_dir) / "recommendation_evaluation.json"),
                "alerts": str(Path(output_dir) / "recommendation_alerts.json"),
                "manifest": str(Path(output_dir) / "recommendation_manifest.json"),
                "features_parquet": _child_path(processed_base, "recommendation_features"),
            },
            "feature_mart_artifacts": {
                "summary": str(Path(output_dir) / "feature_mart_summary.json"),
                "freshness": str(Path(output_dir) / "feature_mart_freshness.json"),
                "quality": str(Path(output_dir) / "feature_mart_quality.json"),
                "partitions": str(Path(output_dir) / "feature_mart_partitions.json"),
                "features": str(Path(output_dir) / "feature_mart_features.json"),
                "readiness": str(Path(output_dir) / "feature_mart_readiness.json"),
                "products": str(Path(output_dir) / "feature_mart_products.json"),
                "categories": str(Path(output_dir) / "feature_mart_categories.json"),
                "users": str(Path(output_dir) / "feature_mart_users.json"),
                "base_dir": _child_path(processed_base, "feature_mart"),
            },
            "anomaly_artifacts": {
                "summary": str(Path(output_dir) / "anomaly_summary.json"),
                "alerts": str(Path(output_dir) / "anomaly_alerts.json"),
                "incidents": str(Path(output_dir) / "anomaly_incidents.json"),
                "root_cause": str(Path(output_dir) / "anomaly_root_cause.json"),
                "evaluation": str(Path(output_dir) / "anomaly_evaluation.json"),
                "timeline": str(Path(output_dir) / "anomaly_timeline.json"),
                "rules": str(Path(output_dir) / "anomaly_rules.json"),
                "base_dir": _child_path(processed_base, "anomaly"),
            },
            "lifecycle_artifacts": {
                "summary": str(Path(output_dir) / "lifecycle_summary.json"),
                "segments": str(Path(output_dir) / "lifecycle_segments.json"),
                "risk_queue": str(Path(output_dir) / "lifecycle_risk_queue.json"),
                "category_affinity": str(Path(output_dir) / "lifecycle_category_affinity.json"),
                "rules": str(Path(output_dir) / "lifecycle_rules.json"),
                "base_dir": _child_path(processed_base, "lifecycle"),
            },
            "experiment_artifacts": {
                "summary": str(Path(output_dir) / "experiment_summary.json"),
                "catalog": str(Path(output_dir) / "experiment_catalog.json"),
                "assignments": str(Path(output_dir) / "experiment_assignments.json"),
                "segments": str(Path(output_dir) / "experiment_segments.json"),
                "guardrails": str(Path(output_dir) / "experiment_guardrails.json"),
                "results": str(Path(output_dir) / "experiment_results.json"),
                "uplift": str(Path(output_dir) / "experiment_uplift.json"),
                "base_dir": _child_path(processed_base, "experimentation"),
            },
        }
        metrics["job"] = {
            "run_id": run_id,
            "contract_version": CONTRACT_VERSION,
            "conversion_contract_version": CONVERSION_CONTRACT_VERSION,
            "affinity_contract_version": AFFINITY_CONTRACT_VERSION,
            "attribution_contract_version": ATTRIBUTION_CONTRACT_VERSION,
            "cohort_contract_version": COHORT_CONTRACT_VERSION,
            "cart_recovery_contract_version": CART_RECOVERY_CONTRACT_VERSION,
            "portfolio_contract_version": PORTFOLIO_CONTRACT_VERSION,
            "forecast_contract_version": FORECAST_CONTRACT_VERSION,
            "journey_contract_version": JOURNEY_CONTRACT_VERSION,
            "anomaly_contract_version": ANOMALY_CONTRACT_VERSION,
            "feature_mart_contract_version": FEATURE_MART_CONTRACT_VERSION,
            "lifecycle_contract_version": LIFECYCLE_CONTRACT_VERSION,
            "experiment_contract_version": EXPERIMENT_CONTRACT_VERSION,
            "optimization_contract_version": OPTIMIZATION_CONTRACT_VERSION,
            "recommendation_contract_version": RECOMMENDATION_CONTRACT_VERSION,
            "dashboard_cube_contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
            "dashboard_semantic_version": DASHBOARD_SEMANTIC_VERSION,
            "elapsed_seconds": elapsed_seconds,
            "cleaned_rows_per_second": cleaned_rows_per_second,
            "spark_application_id": spark_application_id,
            "spark_application_status": "SUCCEEDED" if quality_gate["status"] != "failed" else "FAILED",
            "driver_peak_memory_mb": _driver_peak_memory_mb(),
            "input_path": actual_input_path,
            "configured_input_path": data_config["input_path"],
            "input_format": data_config.get("input_format", "csv"),
            "storage_mode": config.get("storage", {}).get("mode", "local"),
            "config_hash": config_hash(config),
            "input_snapshot": input_snapshot,
            "quality_status": quality_gate["status"],
            "quality_report": {"metrics": quality, "gate": quality_gate},
            "output_artifacts": output_artifacts,
            "output_artifact_row_counts": output_artifact_row_counts,
            "failure_stage": "quality_gate" if quality_gate["status"] == "failed" else None,
        }

        manifest = {
            "run_id": run_id,
            "contract_version": CONTRACT_VERSION,
            "conversion_contract_version": CONVERSION_CONTRACT_VERSION,
            "affinity_contract_version": AFFINITY_CONTRACT_VERSION,
            "attribution_contract_version": ATTRIBUTION_CONTRACT_VERSION,
            "cohort_contract_version": COHORT_CONTRACT_VERSION,
            "cart_recovery_contract_version": CART_RECOVERY_CONTRACT_VERSION,
            "portfolio_contract_version": PORTFOLIO_CONTRACT_VERSION,
            "forecast_contract_version": FORECAST_CONTRACT_VERSION,
            "journey_contract_version": JOURNEY_CONTRACT_VERSION,
            "anomaly_contract_version": ANOMALY_CONTRACT_VERSION,
            "lifecycle_contract_version": LIFECYCLE_CONTRACT_VERSION,
            "experiment_contract_version": EXPERIMENT_CONTRACT_VERSION,
            "optimization_contract_version": OPTIMIZATION_CONTRACT_VERSION,
            "dashboard_cube_contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
            "dashboard_semantic_version": DASHBOARD_SEMANTIC_VERSION,
            "status": "succeeded" if quality_gate["status"] != "failed" else "rejected",
            "elapsed_seconds": elapsed_seconds,
            "cleaned_rows_per_second": cleaned_rows_per_second,
            "spark_application_id": spark_application_id,
            "spark_application_status": "SUCCEEDED" if quality_gate["status"] != "failed" else "FAILED",
            "driver_peak_memory_mb": metrics["job"]["driver_peak_memory_mb"],
            "config_hash": metrics["job"]["config_hash"],
            "input_snapshot": input_snapshot,
            "quality_status": quality_gate["status"],
            "quality_report": metrics["job"]["quality_report"],
            "output_artifacts": output_artifacts,
            "output_artifact_row_counts": output_artifact_row_counts,
            "session_fact_rows": quality["session_fact_rows"],
            "ordering_anomaly_sessions": quality["ordering_anomaly_sessions"],
            "purchase_missing_price_rows": quality["purchase_missing_price_rows"],
            "forecast_quality_status": metrics["forecasting_summary"]["quality_status"],
            "forecast_risk_count": metrics["forecasting_summary"]["risk_count"],
            "affinity_quality_status": metrics["affinity_summary"]["quality_status"],
            "affinity_edge_count": metrics["affinity_summary"]["edge_count"],
            "affinity_opportunity_count": metrics["affinity_summary"]["opportunity_count"],
            "attribution_quality_status": metrics["attribution_summary"]["quality_status"],
            "attribution_coverage_rate": metrics["attribution_summary"]["attribution_coverage_rate"],
            "attribution_assist_opportunity_count": metrics["attribution_summary"]["assist_opportunity_count"],
            "cohort_quality_status": metrics["cohort_summary"]["quality_status"],
            "cohort_repeat_purchase_rate": metrics["cohort_summary"]["repeat_purchase_rate"],
            "cohort_high_risk_count": metrics["cohort_summary"]["high_risk_cohort_count"],
            "cart_recovery_quality_status": metrics["cart_summary"]["quality_status"],
            "cart_abandonment_rate": metrics["cart_summary"]["abandonment_rate"],
            "cart_abandoned_value": metrics["cart_summary"]["abandoned_value"],
            "portfolio_quality_status": metrics["portfolio_summary"]["quality_status"],
            "portfolio_opportunity_count": metrics["portfolio_summary"]["opportunity_count"],
            "portfolio_product_revenue_hhi": metrics["portfolio_summary"]["product_revenue_hhi"],
            "journey_unique_paths": metrics["journey_summary"]["unique_paths"],
            "journey_purchase_path_rate": metrics["journey_summary"]["purchase_path_rate"],
            "optimization_solver_status": metrics["optimization_summary"]["solver_status"],
            "optimization_selected_count": metrics["optimization_summary"]["selected_count"],
            "feature_mart_quality_status": metrics["feature_mart_summary"]["quality_status"],
            "feature_mart_written_partitions": metrics["feature_mart_partitions"]["written"],
            "anomaly_radar_status": metrics["anomaly_summary"]["radar_status"],
            "anomaly_alert_count": metrics["anomaly_summary"]["alert_count"],
            "lifecycle_user_count": metrics["lifecycle_summary"]["user_count"],
            "lifecycle_at_risk_users": metrics["lifecycle_summary"]["at_risk_users"],
            "experiment_guardrail_status": metrics["experiment_summary"]["guardrail_status"],
            "experiment_assignment_rows": metrics["experiment_summary"]["assignment_rows"],
            "recommendation_quality_status": metrics["recommendation_summary"]["quality_status"],
            "recommendation_count": metrics["recommendation_summary"]["recommendation_count"],
            "dashboard_cube_rows": metrics["dashboard_cube_summary"]["cube_row_count"],
            "decision_status": "succeeded",
            "decision_intervention_count": decision_metrics["summary"]["intervention_count"],
            "decision_restock_order_count": decision_metrics["summary"]["restock_order_count"],
            "decision_total_restock_cost": decision_metrics["summary"]["total_estimated_restock_cost"],
            "failure_stage": metrics["job"]["failure_stage"],
        }

        if quality_gate["status"] == "failed":
            manifest["processed_sink_status"] = "skipped_quality_gate"
            metrics["job"]["processed_sink_status"] = manifest["processed_sink_status"]
            write_json_atomic(Path(output_dir) / "runs" / run_id / "manifest.json", manifest)
            write_json_atomic(Path(output_dir) / "run_manifest.json", manifest)
            print(f"Spark run manifest: {output_artifacts['run_manifest_path']}")
            raise RuntimeError("quality gate failed")

        try:
            table_events = cleaned_df.select(*TABLE_EVENT_COLUMNS)
            _write_csv(table_events, str(Path(output_dir) / "table_events"))
            _write_csv(dashboard_cube_frames["dashboard_cube_total"], str(Path(output_dir) / "dashboard_cube_total"))
            _write_csv(dashboard_cube_frames["dashboard_cube_daily"], str(Path(output_dir) / "dashboard_cube_daily"))
            processed_dir = data_config.get("processed_dir")
            if processed_dir:
                processed_path = str(processed_dir).rstrip("/")
                if not processed_path.startswith("hdfs://"):
                    local_processed_path = Path(processed_path)
                    if local_processed_path.exists():
                        shutil.rmtree(local_processed_path)
                cleaned_events = cleaned_df.withColumn("dt", F.col("event_date").cast("string"))
                _write_parquet(cleaned_events, _child_path(processed_path, "events"), partition_cols=["dt"])
                _write_parquet(session_facts, _child_path(processed_path, "session_facts"))
                dashboard_cube_path = _child_path(processed_path, "dashboard_cube")
                _write_parquet(dashboard_cube_frames["dashboard_cube_total"], _child_path(dashboard_cube_path, "total"))
                _write_parquet(dashboard_cube_frames["dashboard_cube_daily"], _child_path(dashboard_cube_path, "daily"), partition_cols=["dt"])
                forecasting_path = _child_path(processed_path, "forecasting")
                for name, frame in forecast_frames.items():
                    _write_parquet(frame, _child_path(forecasting_path, name), partition_cols=["dt"])
                affinity_path = _child_path(processed_path, "affinity")
                for name, frame in affinity_frames.items():
                    _write_parquet(frame, _child_path(affinity_path, name))
                attribution_path = _child_path(processed_path, "attribution")
                for name, frame in attribution_frames.items():
                    _write_parquet(frame, _child_path(attribution_path, name))
                cohort_path = _child_path(processed_path, "cohort_retention")
                for name, frame in cohort_frames.items():
                    _write_parquet(frame, _child_path(cohort_path, name))
                cart_recovery_path = _child_path(processed_path, "cart_recovery")
                for name, frame in cart_recovery_frames.items():
                    _write_parquet(frame, _child_path(cart_recovery_path, name))
                portfolio_path = _child_path(processed_path, "portfolio")
                for name, frame in portfolio_frames.items():
                    _write_parquet(frame, _child_path(portfolio_path, name), partition_cols=["dt"])
                journey_path = _child_path(processed_path, "journey")
                for name, frame in journey_frames.items():
                    _write_parquet(frame, _child_path(journey_path, name))
                _write_parquet(candidates_df, _child_path(processed_path, "optimization_candidates"))
                _write_parquet(recommendation_features, _child_path(processed_path, "recommendation_features"))
                feature_mart_path = _child_path(processed_path, "feature_mart")
                for name, frame in feature_mart_frames.items():
                    _write_parquet(frame, _child_path(feature_mart_path, name), partition_cols=["dt"])
                anomaly_path = _child_path(processed_path, "anomaly")
                for name, frame in anomaly_frames.items():
                    _write_parquet(frame, _child_path(anomaly_path, name), partition_cols=["dt"])
                lifecycle_path = _child_path(processed_path, "lifecycle")
                for name, frame in lifecycle_frames.items():
                    _write_parquet(frame, _child_path(lifecycle_path, name))
                experiment_path = _child_path(processed_path, "experimentation")
                for name, frame in experiment_frames.items():
                    _write_parquet(frame, _child_path(experiment_path, name))
                manifest["processed_sink_status"] = "succeeded"
            else:
                manifest["processed_sink_status"] = "not_configured"
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["spark_application_status"] = "FAILED"
            manifest["failure_stage"] = "processed_sink"
            manifest["processed_sink_status"] = "failed"
            manifest["processed_sink_error"] = str(exc)
            metrics["job"]["spark_application_status"] = "FAILED"
            metrics["job"]["failure_stage"] = "processed_sink"
            metrics["job"]["processed_sink_status"] = "failed"
            metrics["job"]["processed_sink_error"] = str(exc)
            write_json_atomic(Path(output_dir) / "runs" / run_id / "manifest.json", manifest)
            write_json_atomic(Path(output_dir) / "run_manifest.json", manifest)
            print(f"Spark run manifest: {output_artifacts['run_manifest_path']}")
            raise

        metrics["job"]["processed_sink_status"] = manifest["processed_sink_status"]
        metrics["job"]["failure_stage"] = manifest["failure_stage"]
        write_metric_files(data_config.get("output_dir", "data/cache"), metrics)
        write_json_atomic(Path(output_dir) / "runs" / run_id / "manifest.json", manifest)
        write_json_atomic(Path(output_dir) / "run_manifest.json", manifest)

        return metrics
    finally:
        spark.catalog.clearCache()
        spark.stop()


def _child_path(base: str, child: str) -> str:
    return f"{base.rstrip('/')}/{child}"


def _write_parquet(frame: DataFrame, path: str, partition_cols: list[str] | None = None) -> None:
    writer = frame.write.mode("overwrite")
    available_partitions = [column for column in partition_cols or [] if column in frame.columns]
    if available_partitions:
        writer = writer.partitionBy(*available_partitions)
    writer.parquet(path)
    frame.unpersist()


def _write_csv(frame: DataFrame, path: str) -> None:
    frame.write.mode("overwrite").option("header", True).csv(path)


def _unpersist_frames(*items: object) -> None:
    for item in items:
        if isinstance(item, DataFrame):
            item.unpersist()
            continue
        if isinstance(item, dict):
            for frame in item.values():
                if isinstance(frame, DataFrame):
                    frame.unpersist()


def _driver_peak_memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_value = usage if sys.platform == "darwin" else usage * 1024
    return round(bytes_value / (1024 * 1024), 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ecommerce dashboard metrics with PySpark.")
    parser.add_argument("--config", default="configs/local.yaml", help="Path to YAML config.")
    parser.add_argument("--run-id", default=None, help="Stable run id for job governance.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = run_job(load_config(args.config), run_id=args.run_id)
    summary = metrics["summary"]
    print(f"Spark run manifest: {metrics['job']['output_artifacts']['run_manifest_path']}")
    print(
        "Spark job finished: "
        f"raw={summary['raw_rows']} cleaned={summary['cleaned_rows']} "
        f"sales={summary['total_sales']} elapsed={metrics['job']['elapsed_seconds']}s"
    )


if __name__ == "__main__":
    main()
