from __future__ import annotations

from flask import Blueprint, current_app, request

from app.contracts import build_contract, build_openapi
from app.jobs.governance import job_with_governance
from app.jobs.repository import JobRepository
from app.jobs.service import JobService
from app.responses import api_ok
from app.pipeline.runner import SparkPipelineRunner
from app.services.benchmark_evidence import BenchmarkEvidenceService
from app.services.controlled_query import run_controlled_query
from app.services.live_weather_service import LiveWeatherService
from app.services.metric_cache import CacheNotReadyError
from app.services.metric_cache import MetricCache
from app.services.optimization_impact import OptimizationImpactService
from app.services.spark_runner import SparkRunner

api_bp = Blueprint("api", __name__)


def cache() -> MetricCache:
    return MetricCache(
        current_app.config["METRIC_CACHE_DIR"],
        current_app.config["RAW_DATA_PATH"],
        current_app.config.get("CLEANED_TABLE_PATH"),
    )


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


def benchmark_evidence() -> BenchmarkEvidenceService:
    return BenchmarkEvidenceService(current_app.config["PROJECT_ROOT"])


def optimization_impact() -> OptimizationImpactService:
    return OptimizationImpactService(current_app.config["PROJECT_ROOT"], current_app.config["METRIC_CACHE_DIR"])


def live_weather_service() -> LiveWeatherService:
    return LiveWeatherService(
        project_root=current_app.config["PROJECT_ROOT"],
        config_path=current_app.config["SPARK_CONFIG_PATH"],
        cache_dir=current_app.config["METRIC_CACHE_DIR"],
        live_dir=current_app.config.get("LIVE_DATA_DIR"),
    )


def _job_payload(record):
    return job_with_governance(
        record,
        project_root=current_app.config["PROJECT_ROOT"],
        cache_dir=current_app.config["METRIC_CACHE_DIR"],
    )


def _job_list_payload(job_list):
    return {"total": job_list.total, "rows": [_job_payload(row) for row in job_list.rows]}


def _recommendation_recall_stage(source: str) -> str:
    return {
        "personalized_category": "category_recall",
        "graph_neighbor": "graph_neighbor_recall",
        "optimization_fallback": "popular_fallback",
        "als_implicit": "als_recall",
    }.get(source, source or "unknown")


def _candidate_from_recommendation_item(row: dict) -> dict:
    source = row.get("source") or "unknown"
    score = float(row.get("score") or 0)
    confidence = float(row.get("confidence") or 0)
    return {
        "candidate_id": f"{row.get('user_session', 'unknown')}:{row.get('product_id', 'unknown')}:{source}",
        "user_session": str(row.get("user_session") or "unknown"),
        "user_id": str(row.get("user_id") or "unknown"),
        "product_id": str(row.get("product_id") or "unknown"),
        "brand": row.get("brand") or "unknown",
        "category_level1": row.get("category_level1") or "unknown",
        "rank": int(row.get("rank") or 0),
        "candidate_source": source,
        "recall_stage": _recommendation_recall_stage(source),
        "candidate_stage": "ranked_topk",
        "score": score,
        "ranker_score": min(1.0, max(0.0, score)),
        "source_score": min(1.0, max(0.0, confidence)),
        "conversion_score": score,
        "freshness_score": confidence,
        "affinity_score": float(row.get("affinity_score") or 0),
        "confidence": confidence,
        "ranker_model": "interpretable_rule_ranker_v1",
        "calibration_bucket": "high" if score >= 0.8 else "medium" if score >= 0.5 else "low",
        "reason_codes": list(row.get("reason_codes") or []),
        "fallback_used": bool(row.get("fallback_used")),
        "degraded_from_recommendation_items": True,
    }


def _empty_recommendation_evaluation(summary: dict | None = None) -> dict:
    fallback_rate = float((summary or {}).get("fallback_rate") or 0)
    skipped_metric = {
        "status": "skipped",
        "caveat": "evaluation_cache_missing",
        "evaluated_sessions": 0,
        "predicted_items": 0,
        "hit_count": 0,
        "precision_at_k": None,
        "recall_at_k": None,
        "ndcg_at_k": None,
        "catalog_coverage": 0,
        "fallback_rate": fallback_rate,
    }
    return {
        "contract_version": "nearline-recommendation/v1",
        "run_id": (summary or {}).get("run_id", "evaluation-cache-missing"),
        "top_k": 0,
        "split": {
            "strategy": "not_evaluated",
            "rule_candidate_source": "evaluation_cache_missing",
            "leakage_guard": "not_applicable",
            "train_rows": 0,
            "holdout_rows": 0,
            "evaluated_sessions": 0,
            "production_recommendation_rows": int((summary or {}).get("recommendation_count") or 0),
        },
        "behavior_weights": {"view": 1, "cart": 3, "purchase": 8},
        "model_metrics": [
            {"model_name": "rule_recommendation", **skipped_metric},
            {"model_name": "als_implicit", **skipped_metric, "fallback_rate": 0},
        ],
        "source_mix": [],
        "topk_matrix": [],
        "quality_gates": [
            {
                "name": "recall_at_k_available",
                "actual": None,
                "operator": ">=",
                "expected": 0,
                "passed": False,
            },
            {
                "name": "als_baseline_available",
                "actual": "skipped",
                "operator": "==",
                "expected": "evaluated",
                "passed": False,
            },
        ],
        "degraded_from_summary": bool(summary),
    }


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


@api_bp.get("/dashboard/slice")
def dashboard_slice():
    event_type = request.args.get("event_type", default=None, type=str)
    brand = request.args.get("brand", default=None, type=str)
    category_level1 = request.args.get("category_level1", default=None, type=str)
    return api_ok(
        cache().load_dashboard_slice(
            event_type=event_type,
            brand=brand,
            category_level1=category_level1,
        )
    )


@api_bp.post("/query/controlled")
def controlled_query():
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    if len(query) > 160:
        raise ValueError("query must be 160 characters or fewer")
    return api_ok(run_controlled_query(cache(), query))


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


@api_bp.get("/forecasting/evaluation")
def forecasting_evaluation():
    return api_ok(cache().load_metric("forecasting_evaluation"))


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


@api_bp.get("/affinity/centrality")
def affinity_centrality():
    limit = request.args.get("limit", default=50, type=int)
    community_id = request.args.get("community_id")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    rows = cache().load_metric("affinity_centrality")
    if community_id:
        rows = [row for row in rows if row.get("community_id") == community_id]
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


@api_bp.get("/ops/evidence")
def ops_evidence():
    return api_ok(benchmark_evidence().load())


@api_bp.get("/ops/optimization-impact")
def ops_optimization_impact():
    return api_ok(optimization_impact().load())


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


@api_bp.get("/recommendations/candidates")
def recommendation_candidates():
    limit = request.args.get("limit", default=100, type=int)
    source = request.args.get("source")
    if limit < 1 or limit > 300:
        raise ValueError("limit must be between 1 and 300")
    metric_cache = cache()
    try:
        rows = metric_cache.load_metric("recommendation_candidates")
    except CacheNotReadyError:
        rows = [_candidate_from_recommendation_item(row) for row in metric_cache.load_metric("recommendation_items")]
    if source:
        rows = [row for row in rows if row.get("candidate_source") == source or row.get("recall_stage") == source]
    return api_ok(rows[:limit])


@api_bp.get("/recommendations/quality")
def recommendation_quality():
    return api_ok(cache().load_metric("recommendation_quality"))


@api_bp.get("/recommendations/evaluation")
def recommendation_evaluation():
    metric_cache = cache()
    try:
        return api_ok(metric_cache.load_metric("recommendation_evaluation"))
    except CacheNotReadyError:
        try:
            summary = metric_cache.load_metric("recommendation_summary")
        except CacheNotReadyError:
            summary = None
        return api_ok(_empty_recommendation_evaluation(summary))


@api_bp.get("/recommendations/alerts")
def recommendation_alerts():
    return api_ok(cache().load_metric("recommendation_alerts"))


@api_bp.get("/live-weather/current")
def live_weather_current():
    service = live_weather_service()
    if not service.current_weather_path.exists():
        raise CacheNotReadyError("live weather cache not found: current_weather.json")
    import json

    with service.current_weather_path.open("r", encoding="utf-8") as handle:
        return api_ok(json.load(handle))


@api_bp.get("/live-weather/forecast")
def live_weather_forecast():
    service = live_weather_service()
    if not service.forecast_weather_path.exists():
        raise CacheNotReadyError("live weather forecast cache not found: forecast_weather_24h.json")
    import json

    with service.forecast_weather_path.open("r", encoding="utf-8") as handle:
        return api_ok(json.load(handle))


@api_bp.get("/live-weather/summary")
def live_weather_summary():
    return api_ok(cache().load_metric("live_weather_summary"))


@api_bp.get("/live-training/status")
def live_training_status():
    return api_ok(live_weather_service().load_status())


@api_bp.post("/live-training/refresh")
def live_training_refresh():
    status = live_weather_service().enqueue_refresh()
    return api_ok({"status": status["status"], "run_id": status["run_id"]}), 202


@api_bp.get("/live-training/metrics")
def live_training_metrics():
    return api_ok(cache().load_metric("live_training_metrics"))


@api_bp.get("/live-training/impact")
def live_training_impact():
    return api_ok(cache().load_metric("live_weather_impact"))


@api_bp.get("/live-training/forecast-impact")
def live_training_forecast_impact():
    return api_ok(cache().load_metric("live_weather_forecast_impact"))


@api_bp.get("/anomalies/summary")
def anomaly_summary():
    return api_ok(cache().load_metric("anomaly_summary"))


@api_bp.get("/anomalies/alerts")
def anomaly_alerts():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("anomaly_alerts")[:limit])


@api_bp.get("/anomalies/incidents")
def anomaly_incidents():
    limit = request.args.get("limit", default=50, type=int)
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    return api_ok(cache().load_metric("anomaly_incidents")[:limit])


@api_bp.get("/anomalies/root-cause")
def anomaly_root_cause():
    incident_id = request.args.get("incident_id")
    rows = cache().load_metric("anomaly_root_cause")
    if incident_id:
        rows = [row for row in rows if row.get("incident_id") == incident_id]
    return api_ok(rows)


@api_bp.get("/anomalies/evaluation")
def anomaly_evaluation():
    return api_ok(cache().load_metric("anomaly_evaluation"))


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


@api_bp.get("/experiments/results")
def experiment_results():
    experiment_key = request.args.get("experiment_key")
    try:
        rows = cache().load_metric("experiment_results")
    except CacheNotReadyError:
        rows = []
    if experiment_key:
        rows = [row for row in rows if row.get("experiment_key") == experiment_key]
    return api_ok(rows)


@api_bp.get("/experiments/uplift")
def experiment_uplift():
    experiment_key = request.args.get("experiment_key")
    try:
        payload = cache().load_metric("experiment_uplift")
    except CacheNotReadyError:
        payload = {
            "contract_version": "growth-experimentation/v1",
            "measurement_status": "not_measurable",
            "causal_valid": False,
            "causal_caveat": "randomized_exposure_and_outcome_required_for_true_uplift",
            "summary": [],
            "deciles": [],
            "quality_gates": [
                {
                    "name": "causal_outcome_available",
                    "actual": "not_measurable",
                    "operator": "==",
                    "expected": "randomized_experiment_results",
                    "passed": False,
                }
            ],
        }
    if not experiment_key:
        return api_ok(payload)
    filtered = {
        **payload,
        "summary": [row for row in payload.get("summary", []) if row.get("experiment_key") == experiment_key],
        "deciles": [row for row in payload.get("deciles", []) if row.get("experiment_key") == experiment_key],
    }
    return api_ok(filtered)


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


@api_bp.get("/feature-mart/features")
def feature_mart_features():
    return api_ok(cache().load_metric("feature_mart_features"))


@api_bp.get("/feature-mart/readiness")
def feature_mart_readiness():
    return api_ok(cache().load_metric("feature_mart_readiness"))


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
        return api_ok(_job_payload(latest))
    return api_ok(cache().load_metric("job"))


@api_bp.get("/jobs")
def jobs():
    limit = request.args.get("limit", default=20, type=int)
    return api_ok(_job_list_payload(job_service().list_jobs(limit=limit)))


@api_bp.post("/jobs")
def create_job():
    job_record = job_service().enqueue_refresh()
    return api_ok(_job_payload(job_record), "job queued"), 202


@api_bp.get("/jobs/<job_id>")
def job_detail(job_id: str):
    return api_ok(_job_payload(job_service().get_job(job_id)))


@api_bp.get("/jobs/<job_id>/lineage")
def job_lineage(job_id: str):
    record = job_service().get_job(job_id)
    governance = _job_payload(record)["governance"]
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
            "governance": governance,
        }
    )


@api_bp.get("/jobs/<job_id>/quality")
def job_quality(job_id: str):
    record = job_service().get_job(job_id)
    governance = _job_payload(record)["governance"]
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
            "governance": governance,
        }
    )


@api_bp.get("/table")
def table_data():
    page = int_arg("page", 1)
    size = int_arg("size", 20)
    event_type = request.args.get("event_type", default=None, type=str)
    brand = request.args.get("brand", default=None, type=str)
    category_level1 = request.args.get("category_level1", default=None, type=str)
    return api_ok(
        cache().load_table(
            page=page,
            size=size,
            event_type=event_type,
            brand=brand,
            category_level1=category_level1,
        )
    )


def int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@api_bp.post("/refresh")
def refresh():
    job_record = job_service().enqueue_refresh()
    return api_ok({"status": "queued", "job_id": job_record.job_id}, "refresh queued"), 202
