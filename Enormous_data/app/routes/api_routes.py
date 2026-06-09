from __future__ import annotations

from flask import Blueprint, current_app, request

from app.contracts import build_contract, build_openapi
from app.jobs.repository import JobRepository
from app.jobs.service import JobService
from app.responses import api_ok
from app.pipeline.runner import SparkPipelineRunner
from app.services.metric_cache import MetricCache
from app.services.spark_runner import SparkRunner

api_bp = Blueprint("api", __name__)


def cache() -> MetricCache:
    return MetricCache(current_app.config["METRIC_CACHE_DIR"], current_app.config["RAW_DATA_PATH"])


def spark_runner() -> SparkRunner:
    return SparkRunner(
        current_app.config["PROJECT_ROOT"],
        current_app.config["SPARK_CONFIG_PATH"],
        current_app.config["METRIC_CACHE_DIR"],
    )


def job_service() -> JobService:
    return JobService(
        repository=JobRepository(current_app.config["JOB_DB_PATH"]),
        runner=SparkPipelineRunner(current_app.config["PROJECT_ROOT"]),
        project_root=current_app.config["PROJECT_ROOT"],
        config_path=current_app.config["SPARK_CONFIG_PATH"],
        cache_dir=current_app.config["METRIC_CACHE_DIR"],
    )


@api_bp.get("/health")
def health():
    return api_ok({"status": "healthy"})


@api_bp.get("/contracts")
def contracts():
    return api_ok(build_contract())


@api_bp.get("/openapi.json")
def openapi():
    return api_ok(build_openapi())


@api_bp.get("/summary")
def summary():
    return api_ok(cache().load_metric("summary"))


@api_bp.get("/events/distribution")
def events_distribution():
    return api_ok(cache().load_metric("event_type_count"))


@api_bp.get("/trend/daily-events")
def trend_daily_events():
    return api_ok(cache().load_metric("daily_events"))


@api_bp.get("/trend/daily-sales")
def trend_daily_sales():
    return api_ok(cache().load_metric("daily_sales"))


@api_bp.get("/ranking/categories")
def ranking_categories():
    return api_ok(cache().load_metric("top_categories"))


@api_bp.get("/ranking/brands")
def ranking_brands():
    return api_ok(cache().load_metric("top_brands"))


@api_bp.get("/conversion/funnel")
def conversion_funnel():
    return api_ok(cache().load_metric("session_funnel"))


@api_bp.get("/conversion/daily")
def conversion_daily():
    return api_ok(cache().load_metric("conversion_segments"))


@api_bp.get("/conversion/products")
def conversion_products():
    limit = request.args.get("limit", default=20, type=int)
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    return api_ok(cache().load_metric("product_conversion")[:limit])


@api_bp.get("/journey/summary")
def journey_summary():
    return api_ok(cache().load_metric("journey_summary"))


@api_bp.get("/journey/paths")
def journey_paths():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("journey_paths")[:limit])


@api_bp.get("/journey/transitions")
def journey_transitions():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("journey_transitions")[:limit])


@api_bp.get("/journey/exit-events")
def journey_exit_events():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("journey_exit_events")[:limit])


@api_bp.get("/journey/purchase-paths")
def journey_purchase_paths():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("journey_purchase_paths")[:limit])


@api_bp.get("/forecasting/summary")
def forecasting_summary():
    return api_ok(cache().load_metric("forecasting_summary"))


@api_bp.get("/forecasting/series")
def forecasting_series():
    scope = request.args.get("scope")
    entity = request.args.get("entity")
    metric = request.args.get("metric")
    rows = cache().load_metric("forecasting_series")
    if scope:
        rows = [row for row in rows if row.get("scope") == scope]
    if entity:
        rows = [row for row in rows if row.get("entity_key") == entity]
    if metric:
        rows = [row for row in rows if row.get("metric") == metric]
    return api_ok(rows)


@api_bp.get("/forecasting/entities")
def forecasting_entities():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("forecasting_entities")[:limit])


@api_bp.get("/forecasting/backtest")
def forecasting_backtest():
    scope = request.args.get("scope")
    entity = request.args.get("entity")
    rows = cache().load_metric("forecasting_backtest")
    if scope:
        rows = [row for row in rows if row.get("scope") == scope]
    if entity:
        rows = [row for row in rows if row.get("entity_key") == entity]
    return api_ok(rows)


@api_bp.get("/forecasting/risks")
def forecasting_risks():
    limit = request.args.get("limit", default=50, type=int)
    severity = request.args.get("severity")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("forecasting_risks")
    if severity:
        rows = [row for row in rows if row.get("severity") == severity]
    return api_ok(rows[:limit])


@api_bp.get("/forecasting/quality")
def forecasting_quality():
    return api_ok(cache().load_metric("forecasting_quality"))


@api_bp.get("/affinity/summary")
def affinity_summary():
    return api_ok(cache().load_metric("affinity_summary"))


@api_bp.get("/affinity/nodes")
def affinity_nodes():
    limit = request.args.get("limit", default=100, type=int)
    entity_type = request.args.get("entity_type")
    query = request.args.get("q")
    if limit < 1 or limit > 300:
        raise ValueError("limit must be between 1 and 300")
    rows = cache().load_metric("affinity_nodes")
    if entity_type:
        rows = [row for row in rows if row.get("entity_type") == entity_type]
    if query:
        needle = query.lower()
        rows = [
            row
            for row in rows
            if needle in str(row.get("entity_id", "")).lower()
            or needle in str(row.get("entity_label", "")).lower()
            or needle in str(row.get("brand", "")).lower()
            or needle in str(row.get("category_level1", "")).lower()
        ]
    return api_ok(rows[:limit])


@api_bp.get("/affinity/edges")
def affinity_edges():
    limit = request.args.get("limit", default=100, type=int)
    entity_id = request.args.get("entity_id")
    relation_type = request.args.get("relation_type")
    if limit < 1 or limit > 300:
        raise ValueError("limit must be between 1 and 300")
    rows = cache().load_metric("affinity_edges")
    if entity_id:
        rows = [row for row in rows if row.get("source_id") == entity_id or row.get("target_id") == entity_id]
    if relation_type:
        rows = [row for row in rows if row.get("relation_type") == relation_type]
    return api_ok(rows[:limit])


@api_bp.get("/affinity/communities")
def affinity_communities():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("affinity_communities")[:limit])


@api_bp.get("/affinity/opportunities")
def affinity_opportunities():
    limit = request.args.get("limit", default=100, type=int)
    opportunity_type = request.args.get("type")
    min_confidence = request.args.get("confidence", default=None, type=float)
    if limit < 1 or limit > 300:
        raise ValueError("limit must be between 1 and 300")
    rows = cache().load_metric("affinity_opportunities")
    if opportunity_type:
        rows = [row for row in rows if row.get("type") == opportunity_type]
    if min_confidence is not None:
        rows = [row for row in rows if float(row.get("confidence") or 0) >= min_confidence]
    return api_ok(rows[:limit])


@api_bp.get("/affinity/quality")
def affinity_quality():
    return api_ok(cache().load_metric("affinity_quality"))


@api_bp.get("/cohorts/summary")
def cohort_summary():
    return api_ok(cache().load_metric("cohort_summary"))


@api_bp.get("/cohorts/retention")
def cohort_retention():
    metric = request.args.get("metric")
    cohort = request.args.get("cohort")
    rows = cache().load_metric("cohort_retention_matrix")
    if cohort:
        rows = [row for row in rows if row.get("cohort") == cohort]
    if metric and metric not in {"retention_rate", "repurchase_rate", "revenue"}:
        raise ValueError("metric must be retention_rate, repurchase_rate, or revenue")
    return api_ok(rows)


@api_bp.get("/cohorts/value-curves")
def cohort_value_curves():
    cohort = request.args.get("cohort")
    rows = cache().load_metric("cohort_value_curves")
    if cohort:
        rows = [row for row in rows if row.get("cohort") == cohort]
    return api_ok(rows)


@api_bp.get("/cohorts/repurchase-intervals")
def cohort_repurchase_intervals():
    return api_ok(cache().load_metric("cohort_repurchase_intervals"))


@api_bp.get("/cohorts/segments")
def cohort_segments():
    limit = request.args.get("limit", default=50, type=int)
    category = request.args.get("category")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("cohort_segments")
    if category:
        rows = [row for row in rows if row.get("category_level1") == category]
    return api_ok(rows[:limit])


@api_bp.get("/cohorts/quality")
def cohort_quality():
    return api_ok(cache().load_metric("cohort_quality"))


@api_bp.get("/portfolio/summary")
def portfolio_summary():
    return api_ok(cache().load_metric("portfolio_summary"))


@api_bp.get("/portfolio/categories")
def portfolio_categories():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("portfolio_category_mix")[:limit])


@api_bp.get("/portfolio/brands")
def portfolio_brands():
    limit = request.args.get("limit", default=50, type=int)
    category = request.args.get("category")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("portfolio_brand_mix")
    if category:
        rows = [row for row in rows if row.get("category_level1") == category]
    return api_ok(rows[:limit])


@api_bp.get("/portfolio/price-bands")
def portfolio_price_bands():
    category = request.args.get("category")
    band = request.args.get("price_band")
    rows = cache().load_metric("portfolio_price_bands")
    if category:
        rows = [row for row in rows if row.get("category_level1") == category]
    if band:
        rows = [row for row in rows if row.get("price_band") == band]
    return api_ok(rows)


@api_bp.get("/portfolio/products")
def portfolio_products():
    limit = request.args.get("limit", default=50, type=int)
    category = request.args.get("category")
    brand = request.args.get("brand")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("portfolio_product_concentration")
    if category:
        rows = [row for row in rows if row.get("category_level1") == category]
    if brand:
        rows = [row for row in rows if row.get("brand") == brand]
    return api_ok(rows[:limit])


@api_bp.get("/portfolio/concentration")
def portfolio_concentration():
    return api_ok(cache().load_metric("portfolio_product_concentration"))


@api_bp.get("/portfolio/opportunities")
def portfolio_opportunities():
    limit = request.args.get("limit", default=50, type=int)
    opportunity_type = request.args.get("type")
    min_confidence = request.args.get("confidence", default=None, type=float)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("portfolio_opportunities")
    if opportunity_type:
        rows = [row for row in rows if row.get("opportunity_type") == opportunity_type]
    if min_confidence is not None:
        rows = [row for row in rows if float(row.get("confidence") or 0) >= min_confidence]
    return api_ok(rows[:limit])


@api_bp.get("/portfolio/quality")
def portfolio_quality():
    return api_ok(cache().load_metric("portfolio_quality"))


@api_bp.get("/cart-recovery/summary")
def cart_summary():
    return api_ok(cache().load_metric("cart_summary"))


@api_bp.get("/cart-recovery/categories")
def cart_categories():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("cart_category_segments")[:limit])


@api_bp.get("/cart-recovery/products")
def cart_products():
    category = request.args.get("category")
    brand = request.args.get("brand")
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("cart_product_segments")
    if category:
        rows = [row for row in rows if row.get("category_level1") == category]
    if brand:
        rows = [row for row in rows if row.get("brand") == brand]
    return api_ok(rows[:limit])


@api_bp.get("/cart-recovery/recovery-queue")
def cart_recovery_queue():
    action = request.args.get("action")
    confidence = request.args.get("confidence", type=float)
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("cart_recovery_queue")
    if action:
        rows = [row for row in rows if row.get("recovery_action") == action]
    if confidence is not None:
        rows = [row for row in rows if float(row.get("confidence") or 0) >= confidence]
    return api_ok(rows[:limit])


@api_bp.get("/cart-recovery/quality")
def cart_quality():
    return api_ok(cache().load_metric("cart_quality"))


@api_bp.get("/attribution/summary")
def attribution_summary():
    return api_ok(cache().load_metric("attribution_summary"))


@api_bp.get("/attribution/models")
def attribution_models():
    entity_type = request.args.get("entity_type")
    rows = cache().load_metric("attribution_models")
    if entity_type:
        rows = [row for row in rows if row.get("entity_type") == entity_type]
    return api_ok(rows)


@api_bp.get("/attribution/entities")
def attribution_entities():
    entity_type = request.args.get("entity_type")
    model = request.args.get("model", default="time_decay")
    limit = request.args.get("limit", default=50, type=int)
    if model not in {"first_touch", "last_touch", "linear", "time_decay"}:
        raise ValueError("model must be first_touch, last_touch, linear, or time_decay")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("attribution_entities")
    if entity_type:
        rows = [row for row in rows if row.get("entity_type") == entity_type]
    sort_key = {
        "first_touch": "first_touch_revenue",
        "last_touch": "last_touch_revenue",
        "linear": "linear_assisted_revenue",
        "time_decay": "time_decay_assisted_revenue",
    }[model]
    rows = sorted(rows, key=lambda row: float(row.get(sort_key) or 0), reverse=True)
    return api_ok(rows[:limit])


@api_bp.get("/attribution/paths")
def attribution_paths():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("attribution_paths")[:limit])


@api_bp.get("/attribution/assists")
def attribution_assists():
    entity_type = request.args.get("entity_type")
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("attribution_assists")
    if entity_type:
        rows = [row for row in rows if row.get("entity_type") == entity_type]
    return api_ok(rows[:limit])


@api_bp.get("/attribution/quality")
def attribution_quality():
    return api_ok(cache().load_metric("attribution_quality"))


@api_bp.get("/optimization/summary")
def optimization_summary():
    return api_ok(cache().load_metric("optimization_summary"))


@api_bp.get("/optimization/plan")
def optimization_plan():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    return api_ok(cache().load_metric("optimization_plan")[:limit])


@api_bp.get("/optimization/candidates")
def optimization_candidates():
    limit = request.args.get("limit", default=100, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("optimization_candidates")[:limit])


@api_bp.get("/optimization/quality")
def optimization_quality():
    return api_ok(cache().load_metric("optimization_quality"))


@api_bp.get("/recommendations/summary")
def recommendation_summary():
    return api_ok(cache().load_metric("recommendation_summary"))


@api_bp.get("/recommendations/items")
def recommendation_items():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("recommendation_items")[:limit])


@api_bp.get("/recommendations/quality")
def recommendation_quality():
    return api_ok(cache().load_metric("recommendation_quality"))


@api_bp.get("/recommendations/alerts")
def recommendation_alerts():
    return api_ok(cache().load_metric("recommendation_alerts"))


@api_bp.get("/anomalies/summary")
def anomaly_summary():
    return api_ok(cache().load_metric("anomaly_summary"))


@api_bp.get("/anomalies/alerts")
def anomaly_alerts():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("anomaly_alerts")[:limit])


@api_bp.get("/anomalies/timeline")
def anomaly_timeline():
    return api_ok(cache().load_metric("anomaly_timeline"))


@api_bp.get("/anomalies/rules")
def anomaly_rules():
    return api_ok(cache().load_metric("anomaly_rules"))


@api_bp.get("/lifecycle/summary")
def lifecycle_summary():
    return api_ok(cache().load_metric("lifecycle_summary"))


@api_bp.get("/lifecycle/segments")
def lifecycle_segments():
    return api_ok(cache().load_metric("lifecycle_segments"))


@api_bp.get("/lifecycle/risk-queue")
def lifecycle_risk_queue():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("lifecycle_risk_queue")[:limit])


@api_bp.get("/lifecycle/category-affinity")
def lifecycle_category_affinity():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("lifecycle_category_affinity")[:limit])


@api_bp.get("/lifecycle/rules")
def lifecycle_rules():
    return api_ok(cache().load_metric("lifecycle_rules"))


@api_bp.get("/experiments/summary")
def experiment_summary():
    return api_ok(cache().load_metric("experiment_summary"))


@api_bp.get("/experiments/catalog")
def experiment_catalog():
    return api_ok(cache().load_metric("experiment_catalog"))


@api_bp.get("/experiments/assignments")
def experiment_assignments():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("experiment_assignments")[:limit])


@api_bp.get("/experiments/segments")
def experiment_segments():
    return api_ok(cache().load_metric("experiment_segments"))


@api_bp.get("/experiments/guardrails")
def experiment_guardrails():
    return api_ok(cache().load_metric("experiment_guardrails"))


@api_bp.get("/feature-mart/summary")
def feature_mart_summary():
    return api_ok(cache().load_metric("feature_mart_summary"))


@api_bp.get("/feature-mart/freshness")
def feature_mart_freshness():
    return api_ok(cache().load_metric("feature_mart_freshness"))


@api_bp.get("/feature-mart/quality")
def feature_mart_quality():
    return api_ok(cache().load_metric("feature_mart_quality"))


@api_bp.get("/feature-mart/partitions")
def feature_mart_partitions():
    return api_ok(cache().load_metric("feature_mart_partitions"))


@api_bp.get("/feature-mart/products")
def feature_mart_products():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("feature_mart_products")[:limit])


@api_bp.get("/feature-mart/categories")
def feature_mart_categories():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("feature_mart_categories")[:limit])


@api_bp.get("/feature-mart/users")
def feature_mart_users():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("feature_mart_users")[:limit])


@api_bp.get("/job")
def job():
    latest = job_service().latest_job()
    if latest:
        return api_ok(latest.to_dict())
    return api_ok(cache().load_metric("job"))


@api_bp.get("/jobs")
def jobs():
    limit = request.args.get("limit", default=20, type=int)
    return api_ok(job_service().list_jobs(limit=limit).to_dict())


@api_bp.post("/jobs")
def create_job():
    job_record = job_service().enqueue_refresh()
    return api_ok(job_record.to_dict(), "job queued"), 202


@api_bp.get("/jobs/<job_id>")
def job_detail(job_id: str):
    return api_ok(job_service().get_job(job_id).to_dict())


@api_bp.get("/jobs/<job_id>/lineage")
def job_lineage(job_id: str):
    record = job_service().get_job(job_id)
    return api_ok(
        {
            "job_id": record.job_id,
            "run_id": record.run_id,
            "contract_version": record.contract_version,
            "config_hash": record.config_hash,
            "spark_application_id": record.spark_application_id,
            "spark_application_status": record.spark_application_status,
            "spark_history_metrics_status": record.spark_history_metrics_status,
            "spark_history_metrics_error": record.spark_history_metrics_error,
            "spark_history_metrics": record.spark_history_metrics,
            "input_snapshot": record.input_snapshot,
            "output_artifacts": record.output_artifacts,
        }
    )


@api_bp.get("/jobs/<job_id>/quality")
def job_quality(job_id: str):
    record = job_service().get_job(job_id)
    return api_ok(
        {
            "job_id": record.job_id,
            "run_id": record.run_id,
            "spark_application_id": record.spark_application_id,
            "spark_application_status": record.spark_application_status,
            "spark_history_metrics_status": record.spark_history_metrics_status,
            "spark_history_metrics_error": record.spark_history_metrics_error,
            "spark_history_metrics": record.spark_history_metrics,
            "quality_status": record.quality_status,
            "quality_report": record.quality_report,
            "failure_stage": record.failure_stage,
        }
    )


@api_bp.get("/table")
def table_data():
    page = request.args.get("page", default=1, type=int)
    size = request.args.get("size", default=20, type=int)
    event_type = request.args.get("event_type", default=None, type=str)
    brand = request.args.get("brand", default=None, type=str)
    return api_ok(cache().load_table(page=page, size=size, event_type=event_type, brand=brand))


@api_bp.post("/refresh")
def refresh():
    job_record = job_service().enqueue_refresh()
    return api_ok({"status": "queued", "job_id": job_record.job_id}, "refresh queued"), 202
