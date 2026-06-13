from __future__ import annotations

import csv
import json
import re

import pytest

from app import create_app
from app.jobs.models import JobList, JobRecord
from app.jobs.service import JobNotFoundError
from app.services.spark_runner import SparkJobRunningError


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_client(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    raw_path.write_text(
        "\n".join(
            [
                "event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session",
                "2020-01-01 00:00:00 UTC,view,1,10,electronics.phone,apple,99.9,101,s1",
                "2020-01-01 00:01:00 UTC,purchase,2,11,apparel.shoe,nike,199.9,102,s2",
                "2020-01-01 00:02:00 UTC,purchase,3,12,apparel.shoe,adidas,299.9,103,s3",
            ]
        ),
        encoding="utf-8",
    )
    write_json(cache_dir / "summary.json", {"cleaned_rows": 3})
    write_json(cache_dir / "event_type_count.json", [{"name": "view", "value": 1}, {"name": "purchase", "value": 2}])
    write_json(cache_dir / "daily_events.json", [{"date": "2020-01-01", "value": 3}])
    write_json(cache_dir / "daily_sales.json", [{"date": "2020-01-01", "value": 499.8}])
    write_json(cache_dir / "top_categories.json", [{"name": "apparel", "value": 2}])
    write_json(cache_dir / "top_brands.json", [{"name": "nike", "value": 1}])
    write_json(
        cache_dir / "session_funnel.json",
        {
            "totals": {
                "sessions": 3,
                "view_sessions": 3,
                "cart_sessions": 2,
                "purchase_sessions": 1,
                "view_to_cart_rate": 0.667,
                "cart_to_purchase_rate": 0.5,
                "view_to_purchase_rate": 0.333,
                "avg_purchase_latency_minutes": 4.0,
                "revenue": 499.8,
                "avg_order_value": 499.8,
            },
            "steps": [
                {"step": "view", "sessions": 3, "rate_from_previous": 1.0},
                {"step": "cart", "sessions": 2, "rate_from_previous": 0.667},
                {"step": "purchase", "sessions": 1, "rate_from_previous": 0.5},
            ],
        },
    )
    write_json(
        cache_dir / "conversion_segments.json",
        [{"date": "2020-01-01", "sessions": 3, "purchase_sessions": 1, "view_to_purchase_rate": 0.333, "revenue": 499.8}],
    )
    write_json(
        cache_dir / "product_conversion.json",
        [
            {
                "product_id": "2",
                "brand": "nike",
                "category_level1": "apparel",
                "views": 10,
                "carts": 4,
                "purchases": 2,
                "view_to_cart_rate": 0.4,
                "cart_to_purchase_rate": 0.5,
                "revenue": 399.8,
            },
            {
                "product_id": "3",
                "brand": "adidas",
                "category_level1": "apparel",
                "views": 6,
                "carts": 2,
                "purchases": 1,
                "view_to_cart_rate": 0.333,
                "cart_to_purchase_rate": 0.5,
                "revenue": 299.9,
            },
        ],
    )
    journey_path = {
        "path_signature": "view → cart → purchase",
        "sessions": 12,
        "cart_sessions": 12,
        "purchase_sessions": 8,
        "revenue": 1800.0,
        "avg_steps": 3.0,
        "avg_duration_seconds": 240.0,
        "conversion_rate": 0.667,
        "cart_rate": 1.0,
    }
    journey_transition = {
        "contract_version": "customer-journey-intelligence/v1",
        "from_event": "cart",
        "to_event": "purchase",
        "transitions": 8,
        "sessions": 8,
        "purchase_sessions": 8,
        "revenue": 1800.0,
        "conversion_rate": 1.0,
        "dropoff_hint": "conversion step",
    }
    journey_exit = {
        "last_event": "remove_from_cart",
        "sessions": 4,
        "purchase_sessions": 0,
        "revenue": 0.0,
        "avg_steps": 3.0,
        "exit_share": 0.2,
        "purchase_rate": 0.0,
    }
    write_json(
        cache_dir / "journey_summary.json",
        {
            "contract_version": "customer-journey-intelligence/v1",
            "run_id": "journey-test",
            "sessions": 20,
            "unique_paths": 5,
            "purchase_sessions": 8,
            "cart_sessions": 12,
            "purchase_path_rate": 0.4,
            "cart_path_rate": 0.6,
            "revenue": 1800.0,
            "avg_steps": 2.8,
            "avg_duration_seconds": 210.0,
            "top_path": journey_path,
            "top_exit_event": journey_exit,
            "top_transition": journey_transition,
            "recommended_action": "Use high-volume non-purchase paths to prioritize UX investigations.",
        },
    )
    write_json(cache_dir / "journey_paths.json", [journey_path, {**journey_path, "path_signature": "view → cart"}])
    write_json(cache_dir / "journey_transitions.json", [journey_transition])
    write_json(cache_dir / "journey_exit_events.json", [journey_exit])
    write_json(cache_dir / "journey_purchase_paths.json", [journey_path])
    forecasting_series = {
        "contract_version": "demand-forecasting/v1",
        "dt": "2020-01-03",
        "scope": "site",
        "entity_key": "all",
        "entity_label": "全站",
        "metric": "gmv",
        "forecast_value": 1800.0,
        "lower_bound": 630.0,
        "upper_bound": 2970.0,
        "history_days": 1,
        "model_name": "sparse_baseline_fallback",
        "fallback_reason": "insufficient_history_days",
    }
    forecasting_entity = {
        "contract_version": "demand-forecasting/v1",
        "scope": "site",
        "entity_key": "all",
        "entity_label": "全站",
        "forecast_gmv": 12600.0,
        "forecast_purchase_count": 56.0,
        "recent_gmv": 1800.0,
        "expected_change_rate": 6.0,
        "history_days": 1,
        "risk_level": "high",
        "risk_score": 85,
        "model_name": "sparse_baseline_fallback",
        "fallback_reason": "insufficient_history_days",
        "recommended_action": "Collect more history or reduce forecast granularity before committing spend.",
    }
    forecasting_risk = {
        "contract_version": "demand-forecasting/v1",
        "risk_id": "forecast:site:all",
        "scope": "site",
        "entity_key": "all",
        "entity_label": "全站",
        "severity": "high",
        "risk_type": "insufficient_history",
        "metric": "gmv",
        "evidence": {"history_days": 1, "forecast_gmv": 12600.0},
        "recommended_action": "Collect more history or reduce forecast granularity before committing spend.",
    }
    write_json(
        cache_dir / "forecasting_summary.json",
        {
            "contract_version": "demand-forecasting/v1",
            "run_id": "forecasting-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "forecast_horizon_days": 7,
            "training_window_days": 28,
            "backtest_window_days": 7,
            "history_days": 1,
            "driver_history_rows": 13,
            "max_driver_history_rows": 2000,
            "history_range": {"min_dt": "2020-01-01", "max_dt": "2020-01-01"},
            "entity_count": 2,
            "site_forecast_gmv": 12600.0,
            "site_forecast_purchase_count": 56.0,
            "risk_count": 2,
            "high_risk_count": 2,
            "quality_status": "needs_review",
            "top_risk": forecasting_risk,
            "recommended_action": "Use forecast risks as planning signals.",
        },
    )
    write_json(cache_dir / "forecasting_series.json", [forecasting_series, {**forecasting_series, "metric": "purchase_count"}])
    write_json(cache_dir / "forecasting_entities.json", [forecasting_entity, {**forecasting_entity, "scope": "category", "entity_key": "electronics"}])
    write_json(
        cache_dir / "forecasting_backtest.json",
        [
            {
                "contract_version": "demand-forecasting/v1",
                "dt": "2020-01-01",
                "scope": "site",
                "entity_key": "all",
                "entity_label": "全站",
                "metric": "gmv",
                "actual": 1800.0,
                "forecast": 1700.0,
                "absolute_error": 100.0,
                "error": 100.0,
                "horizon": 1,
                "model_name": "rolling_baseline_backtest",
            }
        ],
    )
    write_json(
        cache_dir / "forecasting_evaluation.json",
        {
            "contract_version": "demand-forecasting/v1",
            "run_id": "forecasting-test",
            "windows": [1, 3, 7],
            "model_metrics": [{"group": "rolling_baseline_backtest", "rows": 1, "wape": 0.055556, "bias": 0.055556}],
            "horizon_metrics": [{"group": "h1", "rows": 1, "wape": 0.055556, "bias": 0.055556}],
            "window_metrics": [{"window_days": 1, "rows": 1, "wape": 0.055556, "bias": 0.055556}],
            "error_distribution": {"max_absolute_error": 100.0, "avg_absolute_error": 100.0, "backtest_rows": 1},
            "quality_gates": [{"name": "site_wape", "actual": 0.055556, "operator": "<=", "expected": 0.35, "passed": True}],
        },
    )
    write_json(cache_dir / "forecasting_risks.json", [forecasting_risk])
    write_json(
        cache_dir / "forecasting_quality.json",
        {
            "contract_version": "demand-forecasting/v1",
            "passed": False,
            "quality_status": "needs_review",
            "checks": [{"name": "minimum_history_days", "actual": 1, "operator": ">=", "expected": 7, "passed": False}],
            "metrics": {"site_history_days": 1, "site_wape": None, "sparse_history": True},
        },
    )
    affinity_edge = {
        "contract_version": "product-affinity-graph/v1",
        "source_id": "1004856",
        "target_id": "1004767",
        "source_type": "product",
        "target_type": "product",
        "source_label": "product 1004856",
        "target_label": "product 1004767",
        "source_brand": "samsung",
        "target_brand": "apple",
        "source_category": "electronics",
        "target_category": "electronics",
        "relation_type": "co_purchase",
        "support": 12,
        "confidence": 0.24,
        "lift": 2.4,
        "jaccard": 0.18,
        "revenue_overlap": 4210.5,
        "sample_sessions": 12,
        "quality_status": "passed",
    }
    affinity_node = {
        "contract_version": "product-affinity-graph/v1",
        "entity_id": "1004856",
        "entity_type": "product",
        "entity_label": "product 1004856",
        "brand": "samsung",
        "category_level1": "electronics",
        "views": 1000,
        "carts": 120,
        "purchases": 80,
        "revenue": 8000.0,
        "degree": 3,
        "weighted_degree": 4.8,
        "community_id": "category:electronics",
    }
    affinity_opportunity = {
        "contract_version": "product-affinity-graph/v1",
        "opportunity_id": "bundle:1004856:1004767:co_purchase",
        "type": "bundle",
        "primary_entity": "1004856",
        "primary_label": "product 1004856",
        "related_entity": "1004767",
        "related_label": "product 1004767",
        "reason_codes": ["co_purchase", "high_lift", "same_category"],
        "estimated_revenue_pool": 4210.5,
        "confidence": 0.24,
        "lift": 2.4,
        "support": 12,
        "risk_level": "low",
        "action": "add_bundle_or_complete-the-look_slot",
    }
    write_json(
        cache_dir / "affinity_summary.json",
        {
            "contract_version": "product-affinity-graph/v1",
            "run_id": "affinity-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "node_count": 2,
            "edge_count": 1,
            "community_count": 1,
            "opportunity_count": 1,
            "eligible_session_count": 20,
            "min_support": 3,
            "quality_status": "passed",
            "sparse_graph": False,
            "strongest_edge": affinity_edge,
            "top_opportunity": affinity_opportunity,
            "recommended_action": "Use high-lift product relationships as cross-sell and bundle candidates.",
        },
    )
    write_json(cache_dir / "affinity_nodes.json", [affinity_node, {**affinity_node, "entity_id": "1004767", "brand": "apple"}])
    write_json(cache_dir / "affinity_edges.json", [affinity_edge, {**affinity_edge, "relation_type": "co_view"}])
    write_json(
        cache_dir / "affinity_communities.json",
        [
            {
                "contract_version": "product-affinity-graph/v1",
                "community_id": "category:electronics",
                "category_level1": "electronics",
                "node_count": 2,
                "edge_count": 1,
                "revenue": 12000.0,
                "top_entities": ["1004856", "1004767"],
                "recommended_action": "Use community neighbors for category-level cross-sell review.",
            }
        ],
    )
    write_json(cache_dir / "affinity_opportunities.json", [affinity_opportunity])
    write_json(
        cache_dir / "affinity_centrality.json",
        [
            {
                "contract_version": "product-affinity-graph/v1",
                "entity_id": "1004856",
                "entity_label": "product 1004856",
                "brand": "samsung",
                "category_level1": "electronics",
                "community_id": "category:electronics",
                "degree": 3,
                "weighted_degree": 4.8,
                "normalized_weighted_degree": 1.0,
                "pagerank_score": 0.92,
                "centrality_score": 0.964,
                "community_size": 2,
                "community_revenue": 12000.0,
                "revenue": 8000.0,
                "views": 1000,
                "purchases": 80,
            }
        ],
    )
    write_json(
        cache_dir / "affinity_quality.json",
        {
            "contract_version": "product-affinity-graph/v1",
            "quality_status": "passed",
            "passed": True,
            "session_count": 30,
            "eligible_session_count": 20,
            "edge_count": 1,
            "min_support": 3,
            "sparse_graph": False,
            "warnings": [],
            "checks": [{"name": "edge_count", "actual": 1, "operator": ">", "expected": 0, "passed": True}],
        },
    )
    cohort_cell = {
        "contract_version": "cohort-retention/v1",
        "cohort": "2020-01",
        "period_index": 0,
        "cohort_users": 2,
        "active_users": 2,
        "purchase_users": 2,
        "retention_rate": 1.0,
        "repurchase_rate": 0.5,
        "revenue": 499.8,
        "quality_status": "passed",
    }
    cohort_segment = {
        "contract_version": "cohort-retention/v1",
        "segment_id": "2020-01:electronics",
        "cohort": "2020-01",
        "category_level1": "electronics",
        "users": 2,
        "repeat_purchase_users": 1,
        "repeat_purchase_rate": 0.5,
        "revenue": 499.8,
        "risk_level": "low",
        "reason_codes": ["stable_repeat_purchase"],
        "recommended_action": "Use this cohort as a repeat-purchase benchmark.",
    }
    write_json(
        cache_dir / "cohort_summary.json",
        {
            "contract_version": "cohort-retention/v1",
            "run_id": "cohort-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "cohort_unit": "month",
            "user_count": 2,
            "purchase_user_count": 2,
            "repeat_purchase_user_count": 1,
            "repeat_purchase_rate": 0.5,
            "median_days_to_second_purchase": "month_1",
            "avg_revenue_per_purchase_user": 249.9,
            "cohort_revenue": 499.8,
            "high_risk_cohort_count": 0,
            "quality_status": "passed",
            "sparse_cohorts": [],
            "recommended_action": "Use cohort retention and repeat purchase curves to prioritize lifecycle plays.",
        },
    )
    write_json(cache_dir / "cohort_retention_matrix.json", [cohort_cell, {**cohort_cell, "period_index": 1, "retention_rate": 0.5}])
    write_json(
        cache_dir / "cohort_repurchase_intervals.json",
        [{"contract_version": "cohort-retention/v1", "bucket": "month_1", "users": 1, "share": 1.0, "avg_revenue": 249.9}],
    )
    write_json(
        cache_dir / "cohort_value_curves.json",
        [
            {
                "contract_version": "cohort-retention/v1",
                "cohort": "2020-01",
                "period_index": 0,
                "revenue": 499.8,
                "cumulative_revenue": 499.8,
                "revenue_per_purchase_user": 249.9,
                "purchase_users": 2,
            }
        ],
    )
    write_json(cache_dir / "cohort_segments.json", [cohort_segment])
    write_json(
        cache_dir / "cohort_quality.json",
        {
            "contract_version": "cohort-retention/v1",
            "quality_status": "passed",
            "passed": True,
            "history_days": 31,
            "cohort_count": 1,
            "min_cohort_users": 2,
            "sparse_cohorts": [],
            "warnings": [],
            "checks": [{"name": "cohort_count", "actual": 1, "operator": ">=", "expected": 1, "passed": True}],
        },
    )
    portfolio_category = {
        "contract_version": "portfolio-intelligence/v1",
        "category_level1": "electronics",
        "views": 100,
        "carts": 12,
        "purchases": 8,
        "revenue": 2400.0,
        "avg_price": 300.0,
        "view_to_cart_rate": 0.12,
        "view_to_purchase_rate": 0.08,
        "cart_to_purchase_rate": 0.666667,
        "revenue_share": 0.8,
        "purchase_share": 0.5,
    }
    portfolio_brand = {
        "contract_version": "portfolio-intelligence/v1",
        "category_level1": "electronics",
        "brand": "apple",
        "views": 50,
        "carts": 7,
        "purchases": 5,
        "revenue": 1800.0,
        "avg_price": 360.0,
        "view_to_purchase_rate": 0.1,
        "revenue_share": 0.6,
        "purchase_share": 0.3125,
    }
    portfolio_band = {
        "contract_version": "portfolio-intelligence/v1",
        "category_level1": "electronics",
        "price_band": "premium",
        "purchases": 5,
        "revenue": 1800.0,
        "avg_price": 360.0,
        "revenue_share": 0.6,
        "purchase_share": 0.3125,
    }
    portfolio_product = {
        "contract_version": "portfolio-intelligence/v1",
        "rank": 1,
        "product_id": "1005115",
        "category_level1": "electronics",
        "brand": "apple",
        "purchases": 3,
        "revenue": 1200.0,
        "revenue_share": 0.4,
        "purchase_share": 0.1875,
        "hhi_contribution": 0.16,
    }
    write_json(
        cache_dir / "portfolio_summary.json",
        {
            "contract_version": "portfolio-intelligence/v1",
            "run_id": "portfolio-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "quality_status": "needs_review",
            "total_revenue": 3000.0,
            "total_purchases": 16,
            "category_count": 2,
            "brand_count": 3,
            "price_band_count": 2,
            "warnings": ["history_days"],
            "top_category": portfolio_category,
            "top_product_revenue_share": 0.4,
            "product_revenue_hhi": 0.18,
            "opportunity_count": 1,
            "recommended_action": "Use portfolio mix, concentration, and price-band gaps to prioritize merchandising reviews.",
        },
    )
    write_json(cache_dir / "portfolio_category_mix.json", [portfolio_category])
    write_json(cache_dir / "portfolio_brand_mix.json", [portfolio_brand])
    write_json(cache_dir / "portfolio_price_bands.json", [portfolio_band])
    write_json(cache_dir / "portfolio_product_concentration.json", [portfolio_product])
    write_json(
        cache_dir / "portfolio_opportunities.json",
        [
            {
                "contract_version": "portfolio-intelligence/v1",
                "opportunity_type": "price_band_mix",
                "entity_type": "category_price_band",
                "entity_id": "electronics",
                "price_band": "premium",
                "impact_score": 1080.0,
                "confidence": 0.8,
                "views": None,
                "purchases": 5,
                "revenue": 1800.0,
                "reason_codes": ["price_band_revenue_pool"],
            }
        ],
    )
    write_json(
        cache_dir / "portfolio_quality.json",
        {
            "contract_version": "portfolio-intelligence/v1",
            "quality_status": "needs_review",
            "passed": False,
            "rows": 120,
            "purchase_rows": 16,
            "history_days": 1,
            "category_count": 2,
            "brand_count": 3,
            "valid_price_purchase_rate": 1.0,
            "price_band_count": 2,
            "warnings": ["history_days"],
            "checks": [{"name": "history_days", "actual": 1, "operator": ">=", "expected": 7, "passed": False}],
        },
    )
    cart_category = {
        "contract_version": "cart-recovery-intelligence/v1",
        "category_level1": "electronics",
        "cart_product_sessions": 10,
        "cart_events": 12,
        "remove_events": 4,
        "recovered_sessions": 3,
        "explicit_remove_sessions": 4,
        "abandoned_sessions": 7,
        "cart_value": 4200.0,
        "abandoned_value": 2600.0,
        "recovery_rate": 0.3,
        "abandonment_rate": 0.7,
        "remove_rate": 0.4,
    }
    cart_product = {
        "contract_version": "cart-recovery-intelligence/v1",
        "rank": 1,
        "product_id": "1005115",
        "category_level1": "electronics",
        "brand": "apple",
        "cart_product_sessions": 5,
        "cart_events": 6,
        "remove_events": 2,
        "recovered_sessions": 1,
        "explicit_remove_sessions": 2,
        "abandoned_sessions": 4,
        "avg_price": 500.0,
        "abandoned_value": 2000.0,
        "recovery_rate": 0.2,
        "abandonment_rate": 0.8,
        "remove_rate": 0.4,
        "priority_score": 1600.0,
    }
    cart_queue_item = {
        "contract_version": "cart-recovery-intelligence/v1",
        "entity_type": "product",
        "entity_id": "1005115",
        "entity_label": "apple / electronics / 1005115",
        "recovery_action": "recovery_offer_or_reminder",
        "priority_score": 1600.0,
        "confidence": 0.9,
        "cart_product_sessions": 5,
        "abandoned_sessions": 4,
        "abandoned_value": 2000.0,
        "abandonment_rate": 0.8,
        "remove_rate": 0.4,
        "reason_codes": ["recovery_offer_or_reminder", "product_cart_abandonment"],
    }
    write_json(
        cache_dir / "cart_summary.json",
        {
            "contract_version": "cart-recovery-intelligence/v1",
            "run_id": "cart-test",
            "quality_status": "needs_review",
            "configured_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "cart_product_sessions": 10,
            "abandoned_sessions": 7,
            "recovered_sessions": 3,
            "explicit_remove_sessions": 4,
            "cart_value": 4200.0,
            "abandoned_value": 2600.0,
            "abandonment_rate": 0.7,
            "recovery_rate": 0.3,
            "remove_rate": 0.4,
            "category_count": 1,
            "product_count": 1,
            "queue_count": 1,
            "warnings": ["history_days"],
        },
    )
    write_json(cache_dir / "cart_category_segments.json", [cart_category])
    write_json(cache_dir / "cart_product_segments.json", [cart_product])
    write_json(cache_dir / "cart_recovery_queue.json", [cart_queue_item])
    write_json(
        cache_dir / "cart_quality.json",
        {
            "contract_version": "cart-recovery-intelligence/v1",
            "quality_status": "needs_review",
            "cart_event_rows": 12,
            "remove_event_rows": 4,
            "cart_product_sessions": 10,
            "history_days": 1,
            "min_cart_sessions": 100,
            "min_history_days": 7,
            "warnings": ["history_days"],
        },
    )
    attribution_entity = {
        "contract_version": "revenue-attribution/v1",
        "rank": 1,
        "entity_type": "category",
        "entity_id": "electronics",
        "entity_label": "electronics",
        "touch_sessions": 8,
        "assisted_purchase_sessions": 6,
        "direct_purchase_sessions": 5,
        "first_touch_revenue": 900.0,
        "last_touch_revenue": 1100.0,
        "linear_assisted_revenue": 1000.0,
        "time_decay_assisted_revenue": 1200.0,
        "direct_revenue": 1300.0,
        "assist_to_direct_ratio": 0.923,
        "assist_rate": 0.75,
        "avg_position_before_purchase": 2.5,
        "avg_minutes_before_purchase": 6.2,
        "cart_touchpoints": 4,
        "view_touchpoints": 10,
        "remove_negative_signal_count": 1,
        "confidence": 0.8,
        "reason_codes": ["multi_touch_driver"],
    }
    attribution_path = {
        "contract_version": "revenue-attribution/v1",
        "path_pattern": "view>cart>purchase",
        "sessions": 10,
        "purchase_sessions": 7,
        "revenue": 1800.0,
        "conversion_rate": 0.7,
        "median_latency_minutes": 4.5,
        "sample_size": 10,
    }
    attribution_assist = {
        "contract_version": "revenue-attribution/v1",
        "entity_type": "category",
        "entity_id": "electronics",
        "entity_label": "electronics",
        "suggested_action": "monitor_assist_entity",
        "priority_score": 960.0,
        "confidence": 0.8,
        "time_decay_assisted_revenue": 1200.0,
        "linear_assisted_revenue": 1000.0,
        "direct_revenue": 1300.0,
        "assist_to_direct_ratio": 0.923,
        "assisted_purchase_sessions": 6,
        "touch_sessions": 8,
        "reason_codes": ["multi_touch_driver"],
    }
    write_json(
        cache_dir / "attribution_summary.json",
        {
            "contract_version": "revenue-attribution/v1",
            "run_id": "attribution-test",
            "quality_status": "needs_review",
            "configured_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
            "purchase_rows": 12,
            "purchase_sessions": 10,
            "attributable_sessions": 9,
            "attributable_purchases": 11,
            "attribution_coverage_rate": 0.9,
            "total_purchase_revenue": 2400.0,
            "assisted_revenue": 1200.0,
            "avg_touchpoints_before_purchase": 2.4,
            "avg_minutes_before_purchase": 6.2,
            "multi_touch_purchase_rate": 0.7,
            "entity_count": 1,
            "assist_opportunity_count": 1,
            "warnings": ["history_days"],
        },
    )
    write_json(
        cache_dir / "attribution_models.json",
        [
            {
                "contract_version": "revenue-attribution/v1",
                "entity_type": "category",
                "entity_count": 1,
                "first_touch_revenue": 900.0,
                "last_touch_revenue": 1100.0,
                "linear_assisted_revenue": 1000.0,
                "time_decay_assisted_revenue": 1200.0,
                "direct_revenue": 1300.0,
            }
        ],
    )
    write_json(cache_dir / "attribution_entities.json", [attribution_entity])
    write_json(cache_dir / "attribution_paths.json", [attribution_path])
    write_json(cache_dir / "attribution_assists.json", [attribution_assist])
    write_json(
        cache_dir / "attribution_quality.json",
        {
            "contract_version": "revenue-attribution/v1",
            "quality_status": "needs_review",
            "purchase_rows": 12,
            "purchase_sessions": 10,
            "attributable_sessions": 9,
            "attribution_coverage_rate": 0.9,
            "session_missing_rate": 0.0,
            "valid_purchase_price_rate": 1.0,
            "history_days": 1,
            "warnings": ["history_days"],
        },
    )
    write_json(
        cache_dir / "optimization_summary.json",
        {
            "contract_version": "merchandising-optimization/v1",
            "solver_status": "optimal",
            "objective_value": 1200.5,
            "runtime_seconds": 0.08,
            "optimality_gap": 0,
            "candidate_count": 2,
            "selected_count": 1,
            "total_budget": 5000,
            "used_budget": 120,
            "budget_utilization": 0.024,
            "slot_count": 8,
            "used_slots": 1,
            "slot_utilization": 0.125,
            "expected_incremental_gmv": 900.0,
            "expected_incremental_purchases": 9.0,
            "average_risk_score": 0.2,
            "category_allocation": {"electronics": 1},
            "action_allocation": {"feature_slot": 1},
            "causal_caveat": "observational",
        },
    )
    plan_row = {
        "product_id": "1004856",
        "brand": "samsung",
        "category_level1": "electronics",
        "action": "feature_slot",
        "action_type": "slot",
        "cost": 120,
        "expected_incremental_gmv": 900,
        "expected_incremental_purchases": 9,
        "objective_contribution": 850,
        "confidence_weight": 0.8,
        "risk_score": 0.2,
        "views": 1000,
        "purchases": 100,
        "baseline_gmv": 5000,
        "avg_price": 100,
    }
    write_json(cache_dir / "optimization_plan.json", [plan_row, {**plan_row, "product_id": "1004767", "brand": "apple"}])
    write_json(
        cache_dir / "optimization_candidates.json",
        [
            {
                "product_id": "1004856",
                "brand": "samsung",
                "category_level1": "electronics",
                "views": 1000,
                "carts": 100,
                "purchases": 80,
                "revenue": 8000,
                "avg_price": 100,
                "purchase_rate_shrunk": 0.08,
                "confidence_weight": 0.8,
                "risk_score": 0.2,
                "baseline_gmv": 7500,
            }
        ],
    )
    write_json(
        cache_dir / "optimization_quality.json",
        {
            "contract_version": "merchandising-optimization/v1",
            "candidate_count": 2,
            "selected_count": 1,
            "eligible_count": 2,
            "solver_status": "optimal",
            "budget_feasible": True,
            "slot_feasible": True,
            "category_cap": 12,
            "brand_cap": 6,
            "min_views": 20,
            "min_confidence": 0.03,
        },
    )
    write_json(
        cache_dir / "recommendation_summary.json",
        {
            "contract_version": "nearline-recommendation/v1",
            "run_id": "recommendation-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "feature_window": {"mode": "nearline_recent_sessions", "target_sessions": 20},
            "generated_at": "2026-06-08T00:00:00+00:00",
            "recommendation_count": 2,
            "covered_sessions": 1,
            "coverage_rate": 1.0,
            "personalized_rate": 0.5,
            "fallback_rate": 0.5,
            "avg_confidence": 0.8,
            "avg_score": 0.09,
            "freshness_lag_minutes": 100,
            "quality_status": "passed",
            "rollback_ready": True,
            "active_snapshot_path": "data/cache/recommendation_items.json",
            "previous_snapshot_path": "data/cache/recommendation_previous_items.json",
        },
    )
    recommendation_row = {
        "user_session": "s1",
        "user_id": "101",
        "rank": 1,
        "product_id": "1004856",
        "brand": "samsung",
        "category_level1": "electronics",
        "score": 0.09,
        "confidence": 0.82,
        "reason_codes": ["category_affinity"],
        "source": "personalized_category",
        "fallback_used": False,
    }
    write_json(cache_dir / "recommendation_items.json", [recommendation_row, {**recommendation_row, "rank": 2, "source": "optimization_fallback"}])
    write_json(
        cache_dir / "recommendation_quality.json",
        {
            "contract_version": "nearline-recommendation/v1",
            "recommendation_count": 2,
            "target_sessions": 1,
            "covered_sessions": 1,
            "coverage_rate": 1.0,
            "fallback_rate": 0.5,
            "personalized_rate": 0.5,
            "avg_confidence": 0.8,
            "freshness_lag_minutes": 100,
            "duplicate_recommendation_rate": 0,
            "invalid_product_rate": 0,
            "passed": True,
            "checks": [],
        },
    )
    write_json(
        cache_dir / "recommendation_evaluation.json",
        {
            "contract_version": "nearline-recommendation/v1",
            "run_id": "recommendation-test",
            "top_k": 5,
            "split": {"strategy": "leave_latest_interaction_per_session", "train_rows": 12, "holdout_rows": 2, "evaluated_sessions": 2},
            "behavior_weights": {"view": 1, "cart": 3, "purchase": 8},
            "model_metrics": [
                {"model_name": "rule_recommendation", "status": "evaluated", "precision_at_k": 0.1, "recall_at_k": 0.5, "ndcg_at_k": 0.4, "catalog_coverage": 0.2, "fallback_rate": 0.5},
                {"model_name": "als_implicit", "status": "skipped", "caveat": "insufficient_training_rows", "precision_at_k": None, "recall_at_k": None, "ndcg_at_k": None, "catalog_coverage": 0, "fallback_rate": 0},
            ],
            "source_mix": [{"source": "personalized_category", "recommendations": 1, "share": 0.5}],
            "topk_matrix": [{"model_name": "rule_recommendation", "user_session": "sess-1", "rank": 1, "product_id": "1004856", "hit": True, "source": "personalized_category", "score": 0.8}],
            "quality_gates": [{"name": "recall_at_k_available", "actual": 0.5, "operator": ">=", "expected": 0, "passed": True}],
        },
    )
    write_json(
        cache_dir / "recommendation_candidates.json",
        [
            {
                "candidate_id": "s1:1004856:personalized_category",
                "user_session": "s1",
                "user_id": "101",
                "product_id": "1004856",
                "brand": "samsung",
                "category_level1": "electronics",
                "rank": 1,
                "candidate_source": "personalized_category",
                "recall_stage": "category_recall",
                "candidate_stage": "ranked_topk",
                "score": 0.09,
                "ranker_score": 1.0,
                "source_score": 1.0,
                "conversion_score": 0.09,
                "freshness_score": 0.82,
                "affinity_score": 0.0,
                "confidence": 0.82,
                "ranker_model": "interpretable_rule_ranker_v1",
                "calibration_bucket": "high",
                "reason_codes": ["category_affinity"],
                "fallback_used": False,
            }
        ],
    )
    write_json(cache_dir / "recommendation_alerts.json", [])
    write_json(
        cache_dir / "feature_mart_summary.json",
        {
            "contract_version": "behavior-feature-mart/v1",
            "run_id": "feature-mart-test",
            "input_snapshot": {"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
            "date_range": {"min_dt": "2020-01-01", "max_dt": "2020-01-02"},
            "partitions": {"expected": 2, "written": 2, "missing": []},
            "freshness": {"max_event_time": "2020-01-02T23:59:59", "freshness_lag_hours": 12, "sla_status": "passed"},
            "quality_status": "passed",
            "raw_rows": 3,
            "cleaned_rows": 3,
            "deduped_event_rows": 3,
        },
    )
    write_json(
        cache_dir / "feature_mart_freshness.json",
        {
            "contract_version": "behavior-feature-mart/v1",
            "run_id": "feature-mart-test",
            "generated_at": "2026-06-08T00:00:00+00:00",
            "min_event_time": "2020-01-01T00:00:00",
            "max_event_time": "2020-01-02T23:59:59",
            "watermark_time": "2019-12-26T23:59:59",
            "late_rows": 0,
            "late_rate": 0,
            "affected_dates": [],
            "freshness_lag_hours": 12,
            "max_freshness_lag_hours": 88333,
            "sla_status": "passed",
        },
    )
    write_json(
        cache_dir / "feature_mart_quality.json",
        {
            "contract_version": "behavior-feature-mart/v1",
            "run_id": "feature-mart-test",
            "raw_rows": 3,
            "cleaned_rows": 3,
            "deduped_event_rows": 3,
            "duplicate_event_keys": 0,
            "duplicate_event_key_rate": 0,
            "invalid_event_type_rows": 0,
            "missing_user_rows": 0,
            "missing_product_rows": 0,
            "purchase_missing_or_invalid_price_rows": 0,
            "null_session_rows": 0,
            "quarantined_rows": 0,
            "quarantined_rate": 0,
            "quality_status": "passed",
            "checks": [{"name": "duplicate_event_key_rate", "actual": 0, "operator": "<=", "expected": 0.01, "passed": True}],
        },
    )
    write_json(
        cache_dir / "feature_mart_partitions.json",
        {
            "contract_version": "behavior-feature-mart/v1",
            "run_id": "feature-mart-test",
            "expected": 2,
            "written": 2,
            "missing": [],
            "min_dt": "2020-01-01",
            "max_dt": "2020-01-02",
            "partitions": [{"dt": "2020-01-01", "rows": 2, "status": "written"}],
        },
    )
    write_json(
        cache_dir / "feature_mart_features.json",
        [
            {
                "contract_version": "behavior-feature-mart/v1",
                "run_id": "feature-test",
                "feature_name": "daily_product_behavior.views",
                "chinese_name": "商品日浏览量",
                "grain": "dt + product_id",
                "source": "cleaned_events.event_type=view",
                "refresh_frequency": "daily",
                "quality_assertions": ["non_negative", "partition_present"],
                "owner": "spark_feature_mart",
            }
        ],
    )
    write_json(
        cache_dir / "feature_mart_readiness.json",
        {
            "contract_version": "behavior-feature-mart/v1",
            "run_id": "feature-test",
            "status": "ready",
            "ready_features": 1,
            "total_features": 1,
            "checks": [{"name": "quality_status", "actual": "passed", "operator": "==", "expected": "passed", "passed": True}],
            "features": [{"feature_name": "daily_product_behavior.views", "chinese_name": "商品日浏览量", "grain": "dt + product_id", "status": "ready", "failed_rules": [], "source": "cleaned_events.event_type=view"}],
            "lineage": [{"from": "raw_events", "to": "cleaned_events", "relation": "clean_and_validate"}],
        },
    )
    write_json(
        cache_dir / "feature_mart_products.json",
        [
            {
                "dt": "2020-01-01",
                "product_id": "1004856",
                "brand": "samsung",
                "category_level1": "electronics",
                "views": 10,
                "carts": 3,
                "purchases": 2,
                "unique_users": 8,
                "unique_sessions": 9,
                "revenue": 300.0,
                "avg_price": 150.0,
                "view_to_cart_rate": 0.3,
                "cart_to_purchase_rate": 0.667,
                "view_to_purchase_rate": 0.2,
            }
        ],
    )
    write_json(
        cache_dir / "feature_mart_categories.json",
        [
            {
                "dt": "2020-01-01",
                "category_level1": "electronics",
                "views": 20,
                "carts": 4,
                "purchases": 2,
                "unique_users": 12,
                "revenue": 300.0,
                "avg_price": 150.0,
                "conversion_rate": 0.1,
            }
        ],
    )
    write_json(
        cache_dir / "feature_mart_users.json",
        [
            {
                "dt": "2020-01-01",
                "user_id": "101",
                "sessions": 2,
                "views": 4,
                "carts": 1,
                "purchases": 1,
                "revenue": 150.0,
                "active_minutes": 12.5,
                "distinct_products": 3,
                "distinct_categories": 2,
                "preferred_category_level1": "electronics",
            }
        ],
    )
    anomaly_alert = {
        "contract_version": "ops-anomaly-radar/v1",
        "run_id": "anomaly-test",
        "dt": "2020-01-02",
        "severity": "critical",
        "alert_code": "category_revenue_spike",
        "entity_type": "category",
        "entity_id": "electronics",
        "entity_label": "electronics",
        "metric": "revenue",
        "actual": 5000.0,
        "baseline": 500.0,
        "delta": 4500.0,
        "delta_rate": 9.0,
        "robust_z": 12.4,
        "direction": "spike",
        "message": "category electronics revenue spike detected on 2020-01-02",
        "recommended_action": "Inspect campaign, bot traffic, price promotion, and downstream capacity before scaling exposure.",
        "incident_id": "incident:2020-01-02:category:electronics:revenue",
        "baseline_mode": "weekday_median_mad",
    }
    write_json(
        cache_dir / "anomaly_summary.json",
        {
            "contract_version": "ops-anomaly-radar/v1",
            "run_id": "anomaly-test",
            "radar_status": "critical",
            "alert_count": 2,
            "critical_count": 1,
            "warning_count": 1,
            "watch_count": 0,
            "signal_count": 80,
            "monitored_entities": 10,
            "monitored_days": 2,
            "critical_signal_count": 1,
            "warning_signal_count": 1,
            "watch_signal_count": 0,
            "max_robust_z": 12.4,
            "date_range": {"min_dt": "2020-01-01", "max_dt": "2020-01-02"},
            "feature_mart_quality_status": "passed",
            "feature_mart_freshness_status": "passed",
            "top_alert": anomaly_alert,
        },
    )
    write_json(cache_dir / "anomaly_alerts.json", [anomaly_alert, {**anomaly_alert, "alert_code": "product_views_drop", "severity": "warning"}])
    anomaly_incident = {
        "contract_version": "ops-anomaly-radar/v1",
        "incident_id": anomaly_alert["incident_id"],
        "run_id": "anomaly-test",
        "dt": "2020-01-02",
        "severity": "critical",
        "entity_type": "category",
        "entity_id": "electronics",
        "entity_label": "electronics",
        "metric": "revenue",
        "alert_count": 1,
        "max_robust_z": 12.4,
        "impact_value": 4500.0,
        "root_cause_contributions": [{"dimension": "category", "value": "electronics", "metric": "revenue", "contribution": 4500.0, "contribution_share": 1.0, "direction": "spike"}],
        "recommended_action": "Inspect campaign, bot traffic, price promotion, and downstream capacity before scaling exposure.",
    }
    write_json(cache_dir / "anomaly_incidents.json", [anomaly_incident])
    write_json(
        cache_dir / "anomaly_root_cause.json",
        [{"contract_version": "ops-anomaly-radar/v1", "incident_id": anomaly_incident["incident_id"], "dt": "2020-01-02", "severity": "critical", "dimension": "category", "value": "electronics", "metric": "revenue", "contribution": 4500.0, "contribution_share": 1.0, "direction": "spike"}],
    )
    write_json(
        cache_dir / "anomaly_evaluation.json",
        {
            "contract_version": "ops-anomaly-radar/v1",
            "run_id": "anomaly-test",
            "baseline": {"seasonal_signal_count": 12, "seasonal_coverage_rate": 0.25, "min_seasonal_points": 3, "min_baseline_points": 3},
            "incidents": {"incident_count": 1, "critical_incidents": 1, "warning_incidents": 0},
            "alert_budget": {"anomaly_signal_count": 2, "signal_count": 48, "anomaly_rate": 0.041667, "max_alerts": 100},
            "quality_gates": [{"name": "incident_budget", "actual": 1, "operator": "<=", "expected": 100, "passed": True}],
        },
    )
    write_json(
        cache_dir / "anomaly_timeline.json",
        [{"dt": "2020-01-02", "signal_count": 40, "critical_count": 1, "warning_count": 1, "watch_count": 0, "max_robust_z": 12.4}],
    )
    write_json(
        cache_dir / "anomaly_rules.json",
        {
            "contract_version": "ops-anomaly-radar/v1",
            "baseline": "median + median absolute deviation across current feature mart window",
            "rules": [{"name": "critical_robust_z", "threshold": 6.0}],
        },
    )
    lifecycle_user = {
        "user_id": "101",
        "lifecycle_segment": "high_value",
        "risk_band": "active_value",
        "sessions": 2,
        "views": 4,
        "carts": 1,
        "purchases": 1,
        "revenue": 650.0,
        "recency_days": 0,
        "preferred_category_level1": "electronics",
        "recommended_action": "Protect experience quality and avoid excessive fallback recommendations.",
    }
    write_json(
        cache_dir / "lifecycle_summary.json",
        {
            "contract_version": "customer-lifecycle-intelligence/v1",
            "run_id": "lifecycle-test",
            "snapshot_dt": "2020-01-02",
            "user_count": 2,
            "purchase_count": 1,
            "revenue": 650.0,
            "at_risk_users": 0,
            "convert_intent_users": 1,
            "high_value_users": 1,
            "avg_recency_days": 0.5,
            "segment_count": 2,
            "top_segment": {"lifecycle_segment": "high_value", "users": 1, "revenue": 650.0, "purchases": 1},
            "rules": {"high_value_revenue": 500, "loyal_purchase_days": 2, "at_risk_recency_days": 14},
        },
    )
    write_json(
        cache_dir / "lifecycle_segments.json",
        [
            {"lifecycle_segment": "high_value", "users": 1, "revenue": 650.0, "purchases": 1, "avg_recency_days": 0},
            {"lifecycle_segment": "cart_intent", "users": 1, "revenue": 0.0, "purchases": 0, "avg_recency_days": 1},
        ],
    )
    write_json(cache_dir / "lifecycle_risk_queue.json", [lifecycle_user, {**lifecycle_user, "user_id": "102", "risk_band": "convert_intent"}])
    write_json(
        cache_dir / "lifecycle_category_affinity.json",
        [{"category_level1": "electronics", "users": 1, "user_revenue": 650.0, "user_purchases": 1, "category_revenue": 650.0}],
    )
    write_json(
        cache_dir / "lifecycle_rules.json",
        {
            "contract_version": "customer-lifecycle-intelligence/v1",
            "model": "deterministic RFM + engagement segmentation",
            "rules": [{"name": "high_value", "threshold": 500}],
        },
    )
    experiment_assignment = {
        "contract_version": "growth-experimentation/v1",
        "source_run_id": "experiment-test",
        "experiment_key": "lifecycle_reactivation",
        "name": "生命周期再激活策略",
        "user_id": "102",
        "variant": "treatment",
        "assignment_bucket": 0.12,
        "lifecycle_segment": "cart_intent",
        "risk_band": "convert_intent",
        "preferred_category_level1": "electronics",
        "sessions": 2,
        "views": 4,
        "carts": 1,
        "purchases": 0,
        "revenue": 0.0,
        "expected_incremental_purchase_prob": 0.035,
        "expected_incremental_gmv": 1.75,
        "policy": "category-personalized recovery and incentive message",
        "primary_metric": "purchase_rate",
    }
    write_json(
        cache_dir / "experiment_summary.json",
        {
            "contract_version": "growth-experimentation/v1",
            "run_id": "experiment-test",
            "experiment_count": 3,
            "assignment_rows": 4,
            "assigned_users": 2,
            "treatment_assignments": 2,
            "control_assignments": 2,
            "treatment_split": 0.5,
            "expected_incremental_gmv": 12.5,
            "expected_incremental_purchases": 0.06,
            "guardrail_status": "passed",
            "recommendation_coverage": {"recommendations": 2, "covered_sessions": 1, "fallback_rate": 0.5, "avg_confidence": 0.8},
            "optimization_selected_count": 1,
            "experiments": [{"experiment_key": "lifecycle_reactivation", "assigned_users": 1}],
            "causal_caveat": "Offline estimates are planning priors only.",
        },
    )
    write_json(
        cache_dir / "experiment_catalog.json",
        [
            {
                "contract_version": "growth-experimentation/v1",
                "experiment_key": "lifecycle_reactivation",
                "name": "生命周期再激活策略",
                "primary_metric": "purchase_rate",
                "secondary_metric": "revenue_per_user",
                "target_rule": "risk_band in convert_intent or at_risk",
                "policy": "category-personalized recovery and incentive message",
                "expected_uplift_rate": 0.035,
                "status": "ready",
                "measurement_window": "7-14 days after exposure",
                "guardrail_metrics": ["variant balance"],
            }
        ],
    )
    write_json(cache_dir / "experiment_assignments.json", [experiment_assignment, {**experiment_assignment, "user_id": "101", "variant": "control"}])
    write_json(
        cache_dir / "experiment_segments.json",
        [
            {
                "experiment_key": "lifecycle_reactivation",
                "lifecycle_segment": "cart_intent",
                "variant": "treatment",
                "users": 1,
                "observed_revenue": 0.0,
                "observed_purchases": 0,
                "expected_incremental_gmv": 1.75,
                "experiment_users": 2,
                "segment_share": 0.5,
            }
        ],
    )
    write_json(
        cache_dir / "experiment_guardrails.json",
        {
            "contract_version": "growth-experimentation/v1",
            "status": "passed",
            "checks": [{"name": "min_assignment_users", "actual": 2, "operator": ">=", "expected": 2, "passed": True}],
            "segment_imbalance": [],
            "recommended_action": "Launch only experiments with sufficient treatment/control balance.",
        },
    )
    write_json(
        cache_dir / "experiment_results.json",
        [
            {
                "contract_version": "growth-experimentation/v1",
                "run_id": "experiment-test",
                "experiment_key": "lifecycle_reactivation",
                "name": "生命周期再激活策略",
                "primary_metric": "purchase_rate",
                "measurement_status": "offline_history_replay",
                "oec_metric": "purchase_rate",
                "treatment_users": 1,
                "control_users": 1,
                "expected_treatment_ratio": 0.5,
                "observed_treatment_ratio": 0.5,
                "srm_chi_square": 0.0,
                "srm_p_value": 1.0,
                "srm_status": "passed",
                "control_mean": 1.0,
                "treatment_mean": 0.0,
                "absolute_lift": -1.0,
                "relative_lift": -1.0,
                "standard_error": None,
                "ci_low": None,
                "ci_high": None,
                "p_value": None,
                "decision": "not_measurable",
                "variant_rows": [],
                "causal_caveat": "offline_history_replay_not_causal",
            }
        ],
    )
    write_json(
        cache_dir / "experiment_uplift.json",
        {
            "contract_version": "growth-experimentation/v1",
            "run_id": "experiment-test",
            "measurement_status": "offline_history_replay",
            "causal_valid": False,
            "causal_caveat": "randomized_exposure_and_outcome_required_for_true_uplift",
            "summary": [{"experiment_key": "lifecycle_reactivation", "auuc": 0.0, "qini_auc": 0.0, "decile_count": 1}],
            "deciles": [
                {
                    "experiment_key": "lifecycle_reactivation",
                    "decile": 1,
                    "treatment_users": 1,
                    "control_users": 1,
                    "treatment_conversion_rate": 0.0,
                    "control_conversion_rate": 1.0,
                    "uplift": -1.0,
                    "cumulative_gain": -1.0,
                    "avg_uplift_score": 0.035,
                }
            ],
            "quality_gates": [{"name": "causal_outcome_available", "actual": "offline_history_replay", "operator": "==", "expected": "randomized_experiment_results", "passed": False}],
        },
    )
    write_json(cache_dir / "job.json", {"status": "idle"})

    app = create_app()
    app.config.update(TESTING=True, METRIC_CACHE_DIR=cache_dir, RAW_DATA_PATH=raw_path, JOB_DB_PATH=tmp_path / "platform.db")
    return app.test_client(), cache_dir, raw_path


def test_summary_api_reads_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "summary.json").write_text(json.dumps({"cleaned_rows": 10}), encoding="utf-8")
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")

    app = create_app()
    app.config.update(TESTING=True, METRIC_CACHE_DIR=cache_dir, RAW_DATA_PATH=raw_path, JOB_DB_PATH=tmp_path / "platform.db")
    client = app.test_client()

    response = client.get("/api/v1/summary")

    assert response.status_code == 200
    assert response.get_json()["data"] == {"cleaned_rows": 10}
    assert "request_id" in response.get_json()["meta"]


def test_controlled_query_api_returns_chart_ready_payload(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.post("/api/v1/query/controlled", json={"query": "按月份统计销售额"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["matched"] is True
    assert data["intent"]["metric_label"] == "成交额"
    assert data["intent"]["dimension_label"] == "月份"
    assert data["chart"]["title"] == "按月份统计成交额"
    assert data["rows"] == [{"name": "2020-01", "raw_name": "2020-01", "value": 499.8, "share": 1.0}]
    assert data["evidence"]["execution_engine"] == "dashboard_slice_cache"


def test_controlled_query_api_returns_unsupported_without_500(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.post("/api/v1/query/controlled", json={"query": "随便写一段不在白名单里的问题"})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["matched"] is False
    assert data["status"] == "unsupported"
    assert data["suggestions"]


def test_controlled_query_api_rejects_empty_query(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.post("/api/v1/query/controlled", json={"query": ""})

    assert response.status_code == 400
    assert response.get_json()["message"] == "query is required"


def test_api_contract_lists_stable_endpoints(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/contracts")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    paths = {endpoint["path"] for endpoint in payload["endpoints"]}
    assert payload["version"] == "v1"
    assert "/api/v1/summary" in paths
    assert "/api/v1/openapi.json" in paths
    assert "/api/v1/query/controlled" in paths
    assert "/api/v1/conversion/funnel" in paths
    assert "/api/v1/conversion/daily" in paths
    assert "/api/v1/conversion/products" in paths
    assert "/api/v1/journey/summary" in paths
    assert "/api/v1/journey/paths" in paths
    assert "/api/v1/journey/transitions" in paths
    assert "/api/v1/journey/exit-events" in paths
    assert "/api/v1/journey/purchase-paths" in paths
    assert "/api/v1/forecasting/summary" in paths
    assert "/api/v1/forecasting/series" in paths
    assert "/api/v1/forecasting/entities" in paths
    assert "/api/v1/forecasting/backtest" in paths
    assert "/api/v1/forecasting/evaluation" in paths
    assert "/api/v1/forecasting/risks" in paths
    assert "/api/v1/forecasting/quality" in paths
    assert "/api/v1/affinity/summary" in paths
    assert "/api/v1/affinity/nodes" in paths
    assert "/api/v1/affinity/edges" in paths
    assert "/api/v1/affinity/communities" in paths
    assert "/api/v1/affinity/opportunities" in paths
    assert "/api/v1/affinity/centrality" in paths
    assert "/api/v1/affinity/quality" in paths
    assert "/api/v1/cohorts/summary" in paths
    assert "/api/v1/cohorts/retention" in paths
    assert "/api/v1/cohorts/value-curves" in paths
    assert "/api/v1/cohorts/repurchase-intervals" in paths
    assert "/api/v1/cohorts/segments" in paths
    assert "/api/v1/cohorts/quality" in paths
    assert "/api/v1/portfolio/summary" in paths
    assert "/api/v1/portfolio/categories" in paths
    assert "/api/v1/portfolio/brands" in paths
    assert "/api/v1/portfolio/price-bands" in paths
    assert "/api/v1/portfolio/products" in paths
    assert "/api/v1/portfolio/concentration" in paths
    assert "/api/v1/portfolio/opportunities" in paths
    assert "/api/v1/portfolio/quality" in paths
    assert "/api/v1/cart-recovery/summary" in paths
    assert "/api/v1/cart-recovery/categories" in paths
    assert "/api/v1/cart-recovery/products" in paths
    assert "/api/v1/cart-recovery/recovery-queue" in paths
    assert "/api/v1/cart-recovery/quality" in paths
    assert "/api/v1/attribution/summary" in paths
    assert "/api/v1/attribution/models" in paths
    assert "/api/v1/attribution/entities" in paths
    assert "/api/v1/attribution/paths" in paths
    assert "/api/v1/attribution/assists" in paths
    assert "/api/v1/attribution/quality" in paths
    assert "/api/v1/jobs/{job_id}/lineage" in paths
    assert "/api/v1/jobs/{job_id}/quality" in paths
    assert "/api/v1/ops/evidence" in paths
    assert "/api/v1/ops/optimization-impact" in paths
    assert "/api/v1/optimization/summary" in paths
    assert "/api/v1/optimization/plan" in paths
    assert "/api/v1/optimization/candidates" in paths
    assert "/api/v1/optimization/quality" in paths
    assert "/api/v1/recommendations/summary" in paths
    assert "/api/v1/recommendations/items" in paths
    assert "/api/v1/recommendations/candidates" in paths
    assert "/api/v1/recommendations/quality" in paths
    assert "/api/v1/recommendations/evaluation" in paths
    assert "/api/v1/recommendations/alerts" in paths
    assert "/api/v1/anomalies/summary" in paths
    assert "/api/v1/anomalies/alerts" in paths
    assert "/api/v1/anomalies/incidents" in paths
    assert "/api/v1/anomalies/root-cause" in paths
    assert "/api/v1/anomalies/evaluation" in paths
    assert "/api/v1/anomalies/timeline" in paths
    assert "/api/v1/anomalies/rules" in paths
    assert "/api/v1/lifecycle/summary" in paths
    assert "/api/v1/lifecycle/segments" in paths
    assert "/api/v1/lifecycle/risk-queue" in paths
    assert "/api/v1/lifecycle/category-affinity" in paths
    assert "/api/v1/lifecycle/rules" in paths
    assert "/api/v1/experiments/summary" in paths
    assert "/api/v1/experiments/catalog" in paths
    assert "/api/v1/experiments/assignments" in paths
    assert "/api/v1/experiments/segments" in paths
    assert "/api/v1/experiments/guardrails" in paths
    assert "/api/v1/experiments/results" in paths
    assert "/api/v1/experiments/uplift" in paths
    assert "/api/v1/feature-mart/summary" in paths
    assert "/api/v1/feature-mart/freshness" in paths
    assert "/api/v1/feature-mart/quality" in paths
    assert "/api/v1/feature-mart/partitions" in paths
    assert "/api/v1/feature-mart/features" in paths
    assert "/api/v1/feature-mart/readiness" in paths
    assert "/api/v1/feature-mart/products" in paths
    assert "/api/v1/feature-mart/categories" in paths
    assert "/api/v1/feature-mart/users" in paths
    assert "ApiEnvelope" in payload["schemas"]
    assert "SessionFunnel" in payload["schemas"]
    assert "ProductConversion" in payload["schemas"]
    assert "JourneySummary" in payload["schemas"]
    assert "ForecastingSummary" in payload["schemas"]
    assert "ForecastingEvaluation" in payload["schemas"]
    assert "AffinitySummary" in payload["schemas"]
    assert "AffinityCentrality" in payload["schemas"]
    assert "CohortSummary" in payload["schemas"]
    assert "PortfolioSummary" in payload["schemas"]
    assert "CartSummary" in payload["schemas"]
    assert "AttributionSummary" in payload["schemas"]
    assert "JobLineage" in payload["schemas"]
    assert "JobQuality" in payload["schemas"]
    assert "OptimizationImpact" in payload["schemas"]
    assert "OptimizationSummary" in payload["schemas"]
    assert "RecommendationSummary" in payload["schemas"]
    assert "RecommendationCandidate" in payload["schemas"]
    assert "RecommendationEvaluation" in payload["schemas"]
    assert "AnomalySummary" in payload["schemas"]
    assert "AnomalyIncident" in payload["schemas"]
    assert "LifecycleSummary" in payload["schemas"]
    assert "ExperimentSummary" in payload["schemas"]
    assert "ExperimentResult" in payload["schemas"]
    assert "ExperimentUplift" in payload["schemas"]
    assert "FeatureMartSummary" in payload["schemas"]
    assert "FeatureMartReadiness" in payload["schemas"]
    assert "ControlledQueryResult" in payload["schemas"]
    assert "request_id" in payload["schemas"]["ApiEnvelope"]["properties"]["meta"]["properties"]


def test_api_contract_matches_registered_flask_routes(tmp_path):
    client, _, _ = make_client(tmp_path)
    app = client.application
    contract_paths = {
        (endpoint["method"], endpoint["path"])
        for endpoint in client.get("/api/v1/contracts").get_json()["data"]["endpoints"]
        if endpoint["path"].startswith(("/api/v1", "/healthz", "/readyz"))
    }
    route_paths = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith(("/api/v1", "/healthz", "/readyz")):
            continue
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            route_paths.add((method, path))

    assert route_paths == contract_paths


def test_openapi_exposes_response_schemas(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    spec = response.get_json()["data"]
    contract_paths = {
        endpoint["path"]
        for endpoint in client.get("/api/v1/contracts").get_json()["data"]["endpoints"]
        if endpoint["method"] == "GET"
    }
    assert spec["openapi"] == "3.1.0"
    assert contract_paths <= set(spec["paths"])
    assert "/api/v1/health" in spec["paths"]
    assert "/api/v1/query/controlled" in spec["paths"]
    assert "post" in spec["paths"]["/api/v1/query/controlled"]
    assert "/api/v1/dashboard/slice" in spec["paths"]
    dashboard_slice_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in spec["paths"]["/api/v1/dashboard/slice"]["get"]["parameters"]
    }
    assert dashboard_slice_parameters["event_type"]["enum"] == ["view", "cart", "remove_from_cart", "purchase"]
    assert "category_level1" in dashboard_slice_parameters
    assert "brand" in dashboard_slice_parameters
    assert "/api/v1/table" in spec["paths"]
    table_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in spec["paths"]["/api/v1/table"]["get"]["parameters"]
    }
    assert table_parameters["page"]["minimum"] == 1
    assert table_parameters["size"]["maximum"] == 100
    assert table_parameters["event_type"]["enum"] == ["view", "cart", "remove_from_cart", "purchase"]
    assert "category_level1" in table_parameters
    assert "brand" in table_parameters
    assert "/api/v1/conversion/funnel" in spec["paths"]
    assert "/api/v1/conversion/products" in spec["paths"]
    assert "/api/v1/journey/summary" in spec["paths"]
    assert "/api/v1/journey/transitions" in spec["paths"]
    assert "/api/v1/forecasting/summary" in spec["paths"]
    assert "/api/v1/forecasting/evaluation" in spec["paths"]
    assert "/api/v1/forecasting/risks" in spec["paths"]
    assert "/api/v1/affinity/summary" in spec["paths"]
    assert "/api/v1/affinity/opportunities" in spec["paths"]
    assert "/api/v1/affinity/centrality" in spec["paths"]
    assert "/api/v1/cohorts/summary" in spec["paths"]
    assert "/api/v1/cohorts/retention" in spec["paths"]
    assert "/api/v1/portfolio/summary" in spec["paths"]
    assert "/api/v1/portfolio/opportunities" in spec["paths"]
    assert "/api/v1/cart-recovery/summary" in spec["paths"]
    assert "/api/v1/cart-recovery/recovery-queue" in spec["paths"]
    assert "/api/v1/attribution/summary" in spec["paths"]
    assert "/api/v1/attribution/entities" in spec["paths"]
    assert "/api/v1/attribution/assists" in spec["paths"]
    assert "/api/v1/jobs/{job_id}/lineage" in spec["paths"]
    assert "/api/v1/jobs/{job_id}/quality" in spec["paths"]
    assert "/api/v1/ops/evidence" in spec["paths"]
    assert "/api/v1/ops/optimization-impact" in spec["paths"]
    assert "/api/v1/optimization/summary" in spec["paths"]
    assert "/api/v1/optimization/quality" in spec["paths"]
    assert "/api/v1/recommendations/summary" in spec["paths"]
    assert "/api/v1/recommendations/items" in spec["paths"]
    assert "/api/v1/recommendations/candidates" in spec["paths"]
    assert "/api/v1/recommendations/evaluation" in spec["paths"]
    assert "/api/v1/anomalies/summary" in spec["paths"]
    assert "/api/v1/anomalies/incidents" in spec["paths"]
    assert "/api/v1/anomalies/alerts" in spec["paths"]
    assert "/api/v1/lifecycle/summary" in spec["paths"]
    assert "/api/v1/lifecycle/risk-queue" in spec["paths"]
    assert "/api/v1/experiments/summary" in spec["paths"]
    assert "/api/v1/experiments/assignments" in spec["paths"]
    assert "/api/v1/experiments/results" in spec["paths"]
    assert "/api/v1/experiments/uplift" in spec["paths"]
    assert "/api/v1/feature-mart/summary" in spec["paths"]
    assert "/api/v1/feature-mart/readiness" in spec["paths"]
    assert "/api/v1/feature-mart/products" in spec["paths"]
    assert "Summary" in spec["components"]["schemas"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/health",
        "/api/v1/summary",
        "/api/v1/events/distribution",
        "/api/v1/trend/daily-events",
        "/api/v1/trend/daily-sales",
        "/api/v1/ranking/categories",
        "/api/v1/ranking/brands",
        "/api/v1/conversion/funnel",
        "/api/v1/conversion/daily",
        "/api/v1/conversion/products?limit=1",
        "/api/v1/journey/summary",
        "/api/v1/journey/paths?limit=1",
        "/api/v1/journey/transitions?limit=1",
        "/api/v1/journey/exit-events?limit=1",
        "/api/v1/journey/purchase-paths?limit=1",
        "/api/v1/forecasting/summary",
        "/api/v1/forecasting/series?scope=site&entity=all&metric=gmv",
        "/api/v1/forecasting/entities?limit=1",
        "/api/v1/forecasting/backtest?scope=site&entity=all",
        "/api/v1/forecasting/evaluation",
        "/api/v1/forecasting/risks?severity=high&limit=1",
        "/api/v1/forecasting/quality",
        "/api/v1/affinity/summary",
        "/api/v1/affinity/nodes?entity_type=product&q=samsung&limit=1",
        "/api/v1/affinity/edges?entity_id=1004856&relation_type=co_purchase&limit=1",
        "/api/v1/affinity/communities?limit=1",
        "/api/v1/affinity/opportunities?type=bundle&confidence=0.2&limit=1",
        "/api/v1/affinity/centrality?community_id=category:electronics&limit=1",
        "/api/v1/affinity/quality",
        "/api/v1/cohorts/summary",
        "/api/v1/cohorts/retention?cohort=2020-01&metric=retention_rate",
        "/api/v1/cohorts/value-curves?cohort=2020-01",
        "/api/v1/cohorts/repurchase-intervals",
        "/api/v1/cohorts/segments?category=electronics&limit=1",
        "/api/v1/cohorts/quality",
        "/api/v1/portfolio/summary",
        "/api/v1/portfolio/categories?limit=1",
        "/api/v1/portfolio/brands?category=electronics&limit=1",
        "/api/v1/portfolio/price-bands?category=electronics&price_band=premium",
        "/api/v1/portfolio/products?category=electronics&brand=apple&limit=1",
        "/api/v1/portfolio/concentration",
        "/api/v1/portfolio/opportunities?type=price_band_mix&confidence=0.5&limit=1",
        "/api/v1/portfolio/quality",
        "/api/v1/cart-recovery/summary",
        "/api/v1/cart-recovery/categories?limit=1",
        "/api/v1/cart-recovery/products?category=electronics&brand=apple&limit=1",
        "/api/v1/cart-recovery/recovery-queue?action=recovery_offer_or_reminder&confidence=0.5&limit=1",
        "/api/v1/cart-recovery/quality",
        "/api/v1/attribution/summary",
        "/api/v1/attribution/models?entity_type=category",
        "/api/v1/attribution/entities?entity_type=category&model=time_decay&limit=1",
        "/api/v1/attribution/paths?limit=1",
        "/api/v1/attribution/assists?entity_type=category&limit=1",
        "/api/v1/attribution/quality",
        "/api/v1/optimization/summary",
        "/api/v1/optimization/plan?limit=1",
        "/api/v1/optimization/candidates?limit=1",
        "/api/v1/optimization/quality",
        "/api/v1/recommendations/summary",
        "/api/v1/recommendations/items?limit=1",
        "/api/v1/recommendations/candidates?source=category_recall&limit=1",
        "/api/v1/recommendations/quality",
        "/api/v1/recommendations/evaluation",
        "/api/v1/recommendations/alerts",
        "/api/v1/anomalies/summary",
        "/api/v1/anomalies/alerts?limit=1",
        "/api/v1/anomalies/incidents?limit=1",
        "/api/v1/anomalies/root-cause",
        "/api/v1/anomalies/evaluation",
        "/api/v1/anomalies/timeline",
        "/api/v1/anomalies/rules",
        "/api/v1/lifecycle/summary",
        "/api/v1/lifecycle/segments",
        "/api/v1/lifecycle/risk-queue?limit=1",
        "/api/v1/lifecycle/category-affinity?limit=1",
        "/api/v1/lifecycle/rules",
        "/api/v1/experiments/summary",
        "/api/v1/experiments/catalog",
        "/api/v1/experiments/assignments?limit=1",
        "/api/v1/experiments/segments",
        "/api/v1/experiments/guardrails",
        "/api/v1/experiments/results?experiment_key=lifecycle_reactivation",
        "/api/v1/experiments/uplift?experiment_key=lifecycle_reactivation",
        "/api/v1/feature-mart/summary",
        "/api/v1/feature-mart/freshness",
        "/api/v1/feature-mart/quality",
        "/api/v1/feature-mart/partitions",
        "/api/v1/feature-mart/features",
        "/api/v1/feature-mart/readiness",
        "/api/v1/feature-mart/products?limit=1",
        "/api/v1/feature-mart/categories?limit=1",
        "/api/v1/feature-mart/users?limit=1",
        "/api/v1/job",
        "/api/v1/ops/evidence",
        "/api/v1/ops/optimization-impact",
        "/api/v1/table?page=1&size=2",
    ],
)
def test_v1_api_uses_uniform_envelope(tmp_path, path):
    client, _, _ = make_client(tmp_path)

    response = client.get(path, headers={"X-Request-ID": "req-test-1"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    assert "data" in payload
    assert payload["meta"]["request_id"] == "req-test-1"
    assert response.headers["X-Request-ID"] == "req-test-1"


def test_legacy_api_still_works_with_deprecation_header(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "summary.json").write_text(json.dumps({"cleaned_rows": 10}), encoding="utf-8")
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")

    app = create_app()
    app.config.update(TESTING=True, METRIC_CACHE_DIR=cache_dir, RAW_DATA_PATH=raw_path, JOB_DB_PATH=tmp_path / "platform.db")
    client = app.test_client()

    response = client.get("/api/summary")

    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert response.get_json()["data"] == {"cleaned_rows": 10}


def test_ops_page_serves_react_dist_entry(tmp_path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<main>react ops app</main>", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")
    app = create_app()
    app.config.update(
        TESTING=True,
        PROJECT_ROOT=tmp_path,
        METRIC_CACHE_DIR=cache_dir,
        RAW_DATA_PATH=raw_path,
        JOB_DB_PATH=tmp_path / "platform.db",
    )
    client = app.test_client()

    response = client.get("/ops")

    assert response.status_code == 200
    assert b"react ops app" in response.data


def test_table_page_serves_react_dist_entry_when_available(tmp_path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<main>react table app</main>", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")
    app = create_app()
    app.config.update(
        TESTING=True,
        PROJECT_ROOT=tmp_path,
        METRIC_CACHE_DIR=cache_dir,
        RAW_DATA_PATH=raw_path,
        JOB_DB_PATH=tmp_path / "platform.db",
    )
    client = app.test_client()

    response = client.get("/table?event_type=purchase")

    assert response.status_code == 200
    assert b"react table app" in response.data


def test_table_api_filters_and_paginates(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/table?page=1&size=1&event_type=purchase")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["page"] == 1
    assert data["size"] == 1
    assert data["total"] == 2
    assert len(data["rows"]) == 1
    assert data["rows"][0]["event_type"] == "purchase"
    assert data["source_dataset"] == "raw_events_compatible_fallback"


def test_table_api_filters_by_category_and_brand(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/table?page=1&size=10&event_type=purchase&category_level1=apparel&brand=nike")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total"] == 1
    assert data["rows"][0]["event_type"] == "purchase"
    assert data["rows"][0]["category_level1"] == "apparel"
    assert data["rows"][0]["brand"] == "nike"
    assert data["source_dataset"] == "raw_events_compatible_fallback"
    assert data["rows"][0]["source_dataset"] == "raw_events_compatible_fallback"


def test_dashboard_slice_api_filters_and_returns_evidence(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/dashboard/slice?event_type=purchase&category_level1=apparel&brand=nike")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"]["event_count"] == 1
    assert data["summary"]["purchase_count"] == 1
    assert data["summary"]["total_sales"] == 199.9
    assert data["event_type_count"] == [{"name": "purchase", "value": 1}]
    assert data["daily_events"] == [{"date": "2020-01-01", "value": 1}]
    assert data["daily_sales"] == [{"date": "2020-01-01", "value": 199.9}]
    assert data["top_categories"] == [{"name": "apparel", "value": 1}]
    assert data["evidence"]["filtered_row_count"] == 1
    assert data["evidence"]["total_row_count"] == 3
    assert data["evidence"]["source_dataset"] == "raw_events_compatible_fallback"
    assert data["evidence"]["cache_mode"] == "detail_scan"
    assert data["evidence"]["cache_hit"] is False
    assert data["evidence"]["fallback_reason"] == "dashboard_cube_missing"


def test_table_api_prefers_cleaned_snapshot(tmp_path):
    client, cache_dir, raw_path = make_client(tmp_path)
    table_dir = cache_dir / "table_events"
    table_dir.mkdir()
    with (table_dir / "part-00000.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "event_time": "2020-01-01 00:01:00 UTC",
                "event_type": "purchase",
                "product_id": "cleaned-product",
                "category_id": "11",
                "category_code": "apparel.shoe",
                "category_level1": "apparel",
                "brand": "nike",
                "price": "199.9",
                "user_id": "102",
                "user_session": "s2",
            }
        )
    raw_path.unlink()

    response = client.get("/api/v1/table?page=1&size=10&event_type=purchase&category_level1=apparel&brand=nike")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total"] == 1
    assert data["source_dataset"] == "cleaned_events"
    assert data["rows"][0]["product_id"] == "cleaned-product"


def test_ops_evidence_reads_compact_benchmark_results(tmp_path):
    result_path = (
        tmp_path
        / "data"
        / "benchmarks"
        / "yarn-matrix-1pct-20260609"
        / "yarn_only_csv"
        / "benchmark_results.json"
    )
    result_path.parent.mkdir(parents=True)
    write_json(
        result_path,
        [
            {
                "success": True,
                "input_path": "hdfs:///user/course/ecommerce_behavior_user_sample_1pct/*.csv",
                "input_rows": 100,
                "output_rows": 96,
                "elapsed_seconds": 12.0,
                "spark_application_id": "application_test_0016",
                "spark_application_status": "SUCCEEDED",
                "quality_status": "passed",
                "driver_peak_memory_mb": 120.5,
                "spark_history_metrics_status": "unavailable",
                "error_message": "long stderr should not be returned",
            }
        ],
    )
    write_json(
        result_path.parent / "spark_history_metrics.json",
        {
            "collector": "eventlog",
            "spark_application_id": "application_test_0016",
            "spark_application_status": "SUCCEEDED",
            "task_count": 12,
            "failed_task_count": 0,
            "retried_task_count": 0,
            "shuffle_read_bytes": 1024,
            "shuffle_write_bytes": 512,
            "memory_spill_bytes": 256,
            "disk_spill_bytes": 0,
        },
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")
    app = create_app()
    app.config.update(
        TESTING=True,
        PROJECT_ROOT=tmp_path,
        METRIC_CACHE_DIR=cache_dir,
        RAW_DATA_PATH=raw_path,
        JOB_DB_PATH=tmp_path / "platform.db",
    )
    client = app.test_client()

    response = client.get("/api/v1/ops/evidence")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["benchmark_runs"][0]["spark_application_id"] == "application_test_0016"
    assert data["benchmark_runs"][0]["rows_per_second"] == 8.0
    assert data["benchmark_runs"][0]["spark_history_metrics_status"] == "collected"
    assert data["benchmark_runs"][0]["task_count"] == 12
    assert data["history_summary"]["collected_run_count"] == 1
    assert "error_message" not in data["benchmark_runs"][0]
    assert data["cleanup_policy"]["raw_data_preserved"] is True


def test_ops_optimization_impact_returns_frontend_visible_evidence(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/ops/optimization-impact")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["overall_status"] in {"healthy", "needs_attention"}
    assert data["summary"]["visible_page_count"] == 4
    assert {section["id"] for section in data["frontend_sections"]} == {
        "dashboard",
        "ops",
        "recommendations",
        "forecasting",
    }
    assert any(card["id"] == "feature-mart" for card in data["data_layers"])
    assert any(card["id"] == "recommendation-gate" for card in data["quality_gates"])
    assert any(card["id"] == "forecast-planning" for card in data["model_cards"])
    assert any(card["id"] == "spark-task-health" for card in data["performance_cards"])


def test_table_api_validates_page(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    raw_path = tmp_path / "events.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type", "brand"])
        writer.writeheader()

    app = create_app()
    app.config.update(TESTING=True, METRIC_CACHE_DIR=cache_dir, RAW_DATA_PATH=raw_path, JOB_DB_PATH=tmp_path / "platform.db")
    client = app.test_client()

    response = client.get("/api/v1/table?page=0")

    assert response.status_code == 400
    assert response.get_json()["code"] == 40001
    assert response.get_json()["message"] == "page must be greater than 0"


@pytest.mark.parametrize(("query", "message"), [("page=abc", "page must be an integer"), ("size=abc", "size must be an integer")])
def test_table_api_rejects_non_numeric_pagination(tmp_path, query, message):
    client, _, _ = make_client(tmp_path)

    response = client.get(f"/api/v1/table?{query}")

    assert response.status_code == 400
    assert response.get_json()["code"] == 40001
    assert response.get_json()["message"] == message


def test_conversion_products_validates_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/conversion/products?limit=101")

    assert response.status_code == 400
    assert response.get_json()["code"] == 40001
    assert response.get_json()["message"] == "limit must be between 1 and 100"


def test_conversion_products_applies_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/conversion/products?limit=1")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["product_id"] == "2"


def test_cart_recovery_endpoints_filter_and_validate(tmp_path):
    client, _, _ = make_client(tmp_path)

    products = client.get("/api/v1/cart-recovery/products?category=electronics&brand=apple&limit=1")
    queue = client.get("/api/v1/cart-recovery/recovery-queue?action=recovery_offer_or_reminder&confidence=0.5&limit=1")
    invalid = client.get("/api/v1/cart-recovery/products?limit=201")

    assert products.status_code == 200
    assert products.get_json()["data"][0]["product_id"] == "1005115"
    assert queue.status_code == 200
    assert queue.get_json()["data"][0]["recovery_action"] == "recovery_offer_or_reminder"
    assert invalid.status_code == 400
    assert invalid.get_json()["message"] == "limit must be between 1 and 200"


def test_attribution_endpoints_filter_sort_and_validate(tmp_path):
    client, _, _ = make_client(tmp_path)

    models = client.get("/api/v1/attribution/models?entity_type=category")
    entities = client.get("/api/v1/attribution/entities?entity_type=category&model=time_decay&limit=1")
    assists = client.get("/api/v1/attribution/assists?entity_type=category&limit=1")
    invalid_model = client.get("/api/v1/attribution/entities?model=position_based")
    invalid_limit = client.get("/api/v1/attribution/paths?limit=201")

    assert models.status_code == 200
    assert models.get_json()["data"][0]["entity_type"] == "category"
    assert entities.status_code == 200
    assert entities.get_json()["data"][0]["entity_id"] == "electronics"
    assert assists.status_code == 200
    assert assists.get_json()["data"][0]["suggested_action"] == "monitor_assist_entity"
    assert invalid_model.status_code == 400
    assert invalid_model.get_json()["message"] == "model must be first_touch, last_touch, linear, or time_decay"
    assert invalid_limit.status_code == 400
    assert invalid_limit.get_json()["message"] == "limit must be between 1 and 200"


def test_optimization_plan_and_candidates_apply_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    plan = client.get("/api/v1/optimization/plan?limit=1")
    candidates = client.get("/api/v1/optimization/candidates?limit=1")

    assert plan.status_code == 200
    assert len(plan.get_json()["data"]) == 1
    assert plan.get_json()["data"][0]["action"] == "feature_slot"
    assert candidates.status_code == 200
    assert candidates.get_json()["data"][0]["confidence_weight"] == 0.8


def test_recommendation_items_apply_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/recommendations/items?limit=1")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["source"] == "personalized_category"


def test_stage3_algorithm_evidence_endpoints_filter(tmp_path):
    client, _, _ = make_client(tmp_path)

    candidates = client.get("/api/v1/recommendations/candidates?source=category_recall&limit=1")
    centrality = client.get("/api/v1/affinity/centrality?community_id=category:electronics&limit=1")
    results = client.get("/api/v1/experiments/results?experiment_key=lifecycle_reactivation")
    uplift = client.get("/api/v1/experiments/uplift?experiment_key=lifecycle_reactivation")

    assert candidates.status_code == 200
    assert candidates.get_json()["data"][0]["recall_stage"] == "category_recall"
    assert centrality.status_code == 200
    assert centrality.get_json()["data"][0]["centrality_score"] == 0.964
    assert results.status_code == 200
    assert results.get_json()["data"][0]["srm_status"] == "passed"
    assert uplift.status_code == 200
    assert uplift.get_json()["data"]["causal_valid"] is False
    assert uplift.get_json()["data"]["deciles"][0]["experiment_key"] == "lifecycle_reactivation"


def test_recommendation_candidates_degrade_from_items_when_missing(tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    (cache_dir / "recommendation_candidates.json").unlink()

    response = client.get("/api/v1/recommendations/candidates?source=category_recall&limit=1")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data[0]["candidate_source"] == "personalized_category"
    assert data[0]["recall_stage"] == "category_recall"
    assert data[0]["affinity_score"] == 0
    assert data[0]["degraded_from_recommendation_items"] is True


def test_recommendation_evaluation_degrades_when_missing(tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    (cache_dir / "recommendation_evaluation.json").unlink()

    response = client.get("/api/v1/recommendations/evaluation")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["split"]["strategy"] == "not_evaluated"
    assert data["model_metrics"][0]["status"] == "skipped"
    assert data["quality_gates"][0]["passed"] is False
    assert data["degraded_from_summary"] is True


def test_experiment_optional_evidence_endpoints_degrade_when_missing(tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    (cache_dir / "experiment_results.json").unlink()
    (cache_dir / "experiment_uplift.json").unlink()

    results = client.get("/api/v1/experiments/results")
    uplift = client.get("/api/v1/experiments/uplift")

    assert results.status_code == 200
    assert results.get_json()["data"] == []
    assert uplift.status_code == 200
    payload = uplift.get_json()["data"]
    assert payload["causal_valid"] is False
    assert payload["deciles"] == []
    assert payload["quality_gates"][0]["passed"] is False


def test_feature_mart_preview_endpoints_apply_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    products = client.get("/api/v1/feature-mart/products?limit=1")
    categories = client.get("/api/v1/feature-mart/categories?limit=1")
    users = client.get("/api/v1/feature-mart/users?limit=1")

    assert products.status_code == 200
    assert products.get_json()["data"][0]["product_id"] == "1004856"
    assert categories.status_code == 200
    assert categories.get_json()["data"][0]["category_level1"] == "electronics"
    assert users.status_code == 200
    assert users.get_json()["data"][0]["preferred_category_level1"] == "electronics"


def test_anomaly_alerts_apply_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/anomalies/alerts?limit=1")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["alert_code"] == "category_revenue_spike"


def test_lifecycle_preview_endpoints_apply_limit(tmp_path):
    client, _, _ = make_client(tmp_path)

    risk_queue = client.get("/api/v1/lifecycle/risk-queue?limit=1")
    affinity = client.get("/api/v1/lifecycle/category-affinity?limit=1")

    assert risk_queue.status_code == 200
    assert len(risk_queue.get_json()["data"]) == 1
    assert risk_queue.get_json()["data"][0]["user_id"] == "101"
    assert affinity.status_code == 200
    assert affinity.get_json()["data"][0]["category_level1"] == "electronics"


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("/api/v1/optimization/plan?limit=101", "limit must be between 1 and 100"),
        ("/api/v1/optimization/candidates?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/recommendations/items?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/anomalies/alerts?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/lifecycle/risk-queue?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/lifecycle/category-affinity?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/feature-mart/products?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/feature-mart/categories?limit=201", "limit must be between 1 and 200"),
        ("/api/v1/feature-mart/users?limit=201", "limit must be between 1 and 200"),
    ],
)
def test_optimization_limit_validation(tmp_path, path, message):
    client, _, _ = make_client(tmp_path)

    response = client.get(path)

    assert response.status_code == 400
    assert response.get_json()["message"] == message


@pytest.mark.parametrize("size", [0, 101])
def test_table_api_validates_size(tmp_path, size):
    client, _, _ = make_client(tmp_path)

    response = client.get(f"/api/v1/table?page=1&size={size}")

    assert response.status_code == 400
    assert response.get_json()["code"] == 40001
    assert response.get_json()["message"] == "size must be between 1 and 100"


def test_missing_metric_cache_returns_503(tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    (cache_dir / "summary.json").unlink()

    response = client.get("/api/v1/summary")

    assert response.status_code == 503
    assert response.get_json()["code"] == 50301
    assert response.get_json()["data"] is None


def test_missing_raw_csv_returns_503_for_table(tmp_path):
    client, _, raw_path = make_client(tmp_path)
    raw_path.unlink()

    response = client.get("/api/v1/table")

    assert response.status_code == 503
    assert response.get_json()["code"] == 50301


def test_unknown_api_returns_json_404(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert response.get_json()["code"] == 40401


def test_refresh_returns_202(monkeypatch, tmp_path):
    client, _, _ = make_client(tmp_path)

    class FakeJobService:
        def enqueue_refresh(self):
            return JobRecord(
                job_id="job-1",
                job_type="spark_refresh",
                status="queued",
                config_path="configs/local.yaml",
                input_path="data/raw/*.csv",
                storage_mode="local",
                created_at="2026-06-08T00:00:00+00:00",
            )

    monkeypatch.setattr("app.routes.api_routes.job_service", lambda: FakeJobService())

    response = client.post("/api/v1/refresh")

    assert response.status_code == 202
    assert response.get_json()["data"] == {"status": "queued", "job_id": "job-1"}


def test_refresh_conflict_returns_409(monkeypatch, tmp_path):
    client, _, _ = make_client(tmp_path)

    class FakeJobService:
        def enqueue_refresh(self):
            raise SparkJobRunningError("spark refresh job is already running")

    monkeypatch.setattr("app.routes.api_routes.job_service", lambda: FakeJobService())

    response = client.post("/api/v1/refresh")

    assert response.status_code == 409
    assert response.get_json()["code"] == 40901


def test_jobs_api_creates_and_lists_jobs(monkeypatch, tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    artifact_path = cache_dir / "run_manifest.json"
    write_json(artifact_path, {"run_id": "run-1"})
    job = JobRecord(
        job_id="job-1",
        job_type="spark_refresh",
        status="queued",
        config_path="configs/local.yaml",
        input_path="data/raw/*.csv",
        storage_mode="local",
        created_at="2026-06-08T00:00:00+00:00",
        run_id="run-1",
        contract_version="pipeline-run-governance/v1",
        config_hash="abc123",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv"},
        quality_status="passed",
        quality_report={"gate": {"status": "passed"}},
        output_artifacts={"run_manifest_path": str(artifact_path), "metrics_dir": "data/cache"},
    )

    class FakeJobService:
        def enqueue_refresh(self):
            return job

        def list_jobs(self, limit=20):
            assert limit == 5
            return JobList(total=1, rows=[job])

        def get_job(self, job_id):
            assert job_id == "job-1"
            return job

    monkeypatch.setattr("app.routes.api_routes.job_service", lambda: FakeJobService())

    created = client.post("/api/v1/jobs")
    listed = client.get("/api/v1/jobs?limit=5")
    detail = client.get("/api/v1/jobs/job-1")

    assert created.status_code == 202
    assert created.get_json()["data"]["job_id"] == "job-1"
    assert listed.status_code == 200
    assert listed.get_json()["data"]["total"] == 1
    assert detail.status_code == 200
    assert detail.get_json()["data"]["status"] == "queued"
    assert detail.get_json()["data"]["run_id"] == "run-1"
    assert detail.get_json()["data"]["governance"]["contract_version"] == "job-governance/v1"
    assert detail.get_json()["data"]["governance"]["artifacts"][0]["status"] == "fresh"
    assert listed.get_json()["data"]["rows"][0]["governance"]["active_stage"] == "queued"


def test_job_lineage_and_quality_api(monkeypatch, tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    artifact_path = cache_dir / "runs" / "run-1" / "manifest.json"
    artifact_path.parent.mkdir(parents=True)
    write_json(artifact_path, {"run_id": "run-1"})
    job = JobRecord(
        job_id="job-1",
        job_type="spark_refresh",
        status="succeeded",
        config_path="configs/docker-hdfs.yaml",
        input_path="hdfs://master:9000/user/course/ecommerce_behavior/*.csv",
        storage_mode="hdfs",
        created_at="2026-06-08T00:00:00+00:00",
        run_id="run-1",
        contract_version="pipeline-run-governance/v1",
        config_hash="abc123",
        spark_application_id="application_1",
        spark_application_status="SUCCEEDED",
        spark_history_metrics_status="collected",
        spark_history_metrics={"failed_task_count": 0, "memory_spill_bytes": 0},
        input_snapshot={"file_count": 2, "files": ["hdfs://master:9000/user/course/ecommerce_behavior/2019-Oct.csv"]},
        quality_status="passed",
        quality_report={"gate": {"status": "passed"}, "metrics": {"cleaned_rows": 100}},
        output_artifacts={"run_manifest_path": str(artifact_path)},
    )

    class FakeJobService:
        def get_job(self, job_id):
            assert job_id == "job-1"
            return job

    monkeypatch.setattr("app.routes.api_routes.job_service", lambda: FakeJobService())

    lineage = client.get("/api/v1/jobs/job-1/lineage")
    quality = client.get("/api/v1/jobs/job-1/quality")

    assert lineage.status_code == 200
    assert lineage.get_json()["data"]["input_snapshot"]["file_count"] == 2
    assert lineage.get_json()["data"]["spark_application_status"] == "SUCCEEDED"
    assert lineage.get_json()["data"]["output_artifacts"]["run_manifest_path"].endswith("manifest.json")
    assert lineage.get_json()["data"]["governance"]["status"] == "published"
    assert lineage.get_json()["data"]["governance"]["completion_ratio"] == 1
    assert quality.status_code == 200
    assert quality.get_json()["data"]["quality_status"] == "passed"
    assert quality.get_json()["data"]["quality_report"]["metrics"]["cleaned_rows"] == 100
    assert quality.get_json()["data"]["spark_history_metrics"]["failed_task_count"] == 0
    assert quality.get_json()["data"]["governance"]["quality_summary"]["passed_check_count"] == 0


def test_job_detail_returns_404_for_missing_job(monkeypatch, tmp_path):
    client, _, _ = make_client(tmp_path)

    class FakeJobService:
        def get_job(self, job_id):
            raise JobNotFoundError(f"job not found: {job_id}")

    monkeypatch.setattr("app.routes.api_routes.job_service", lambda: FakeJobService())

    response = client.get("/api/v1/jobs/missing")

    assert response.status_code == 404
    assert response.get_json()["code"] == 40401


def test_healthz_and_readyz(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "summary.json").write_text(json.dumps({"cleaned_rows": 10}), encoding="utf-8")
    raw_path = tmp_path / "events.csv"
    raw_path.write_text("event_type,brand\n", encoding="utf-8")

    app = create_app()
    app.config.update(TESTING=True, METRIC_CACHE_DIR=cache_dir, RAW_DATA_PATH=raw_path, JOB_DB_PATH=tmp_path / "platform.db")
    client = app.test_client()

    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.get_json()["data"]["status"] == "ok"
    assert ready.status_code == 200
    assert ready.get_json()["data"]["status"] == "ready"


def test_readyz_returns_503_when_cache_is_missing(tmp_path):
    client, cache_dir, _ = make_client(tmp_path)
    (cache_dir / "summary.json").unlink()

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.get_json()["data"]["status"] == "not_ready"
    assert response.get_json()["data"]["checks"]["summary_cache"] is False


def test_cors_allows_frontend_origin(tmp_path):
    client, _, _ = make_client(tmp_path)

    response = client.get("/api/v1/summary", headers={"Origin": "http://127.0.0.1:5173"})

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
