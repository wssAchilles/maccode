from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.ranking import with_global_rank


PORTFOLIO_CONTRACT_VERSION = "portfolio-intelligence/v1"

DEFAULT_CONFIG = {
    "preview_limit": 120,
    "min_purchase_rows": 100,
    "min_history_days": 7,
    "min_valid_price_purchase_rate": 0.98,
    "top_products": 100,
}


def portfolio_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_portfolio_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    enriched = enrich_events(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    category_mix = build_category_mix(enriched).persist(StorageLevel.MEMORY_AND_DISK)
    brand_mix = build_brand_mix(enriched).persist(StorageLevel.MEMORY_AND_DISK)
    price_bands = build_price_band_mix(enriched).persist(StorageLevel.MEMORY_AND_DISK)
    product_concentration = build_product_concentration(enriched, config).persist(StorageLevel.MEMORY_AND_DISK)
    opportunities = build_opportunities(category_mix, price_bands, config).persist(StorageLevel.MEMORY_AND_DISK)

    preview_limit = int(config["preview_limit"])
    category_rows = [_row_to_dict(row.asDict(recursive=True)) for row in category_mix.limit(preview_limit).collect()]
    brand_rows = [_row_to_dict(row.asDict(recursive=True)) for row in brand_mix.limit(preview_limit).collect()]
    price_band_rows = [_row_to_dict(row.asDict(recursive=True)) for row in price_bands.limit(preview_limit).collect()]
    concentration_rows = [_row_to_dict(row.asDict(recursive=True)) for row in product_concentration.limit(preview_limit).collect()]
    opportunity_rows = [_row_to_dict(row.asDict(recursive=True)) for row in opportunities.limit(preview_limit).collect()]
    quality = build_quality(enriched, price_bands, config)
    summary = build_summary(
        category_mix,
        product_concentration,
        opportunities,
        category_rows,
        concentration_rows,
        quality,
        config,
        run_id,
        input_snapshot,
    )

    frames = {
        "portfolio_category_mix": category_mix,
        "portfolio_brand_mix": brand_mix,
        "portfolio_price_bands": price_bands,
        "portfolio_product_concentration": product_concentration,
        "portfolio_opportunities": opportunities,
    }
    metrics = {
        "portfolio_summary": summary,
        "portfolio_category_mix": category_rows[:preview_limit],
        "portfolio_brand_mix": brand_rows[:preview_limit],
        "portfolio_price_bands": price_band_rows[:preview_limit],
        "portfolio_product_concentration": concentration_rows[:preview_limit],
        "portfolio_opportunities": opportunity_rows[:preview_limit],
        "portfolio_quality": quality,
    }
    enriched.unpersist()
    return frames, metrics


def enrich_events(cleaned_df: DataFrame) -> DataFrame:
    purchase_price = F.when(F.col("event_type") == "purchase", F.col("price"))
    return (
        cleaned_df.withColumn("dt", F.to_date("event_timestamp"))
        .withColumn("category_level1", F.coalesce(F.col("category_level1"), F.lit("unknown")))
        .withColumn("brand", F.coalesce(F.col("brand"), F.lit("unknown")))
        .withColumn(
            "price_band",
            F.when(purchase_price < 50, F.lit("budget"))
            .when(purchase_price < 200, F.lit("mass"))
            .when(purchase_price < 1000, F.lit("premium"))
            .when(purchase_price >= 1000, F.lit("luxury"))
            .otherwise(F.lit("unknown")),
        )
    )


def aggregate_mix(df: DataFrame, group_cols: list[str]) -> DataFrame:
    grouped = (
        df.groupBy(*group_cols)
        .agg(
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias("views"),
            F.sum(F.when(F.col("event_type") == "cart", 1).otherwise(0)).alias("carts"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
            F.round(F.sum(F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(0)), 2).alias("revenue"),
            F.round(F.avg(F.when(F.col("event_type") == "purchase", F.col("price"))), 2).alias("avg_price"),
        )
        .withColumn("view_to_cart_rate", F.round(F.col("carts") / F.when(F.col("views") == 0, None).otherwise(F.col("views")), 6))
        .withColumn("view_to_purchase_rate", F.round(F.col("purchases") / F.when(F.col("views") == 0, None).otherwise(F.col("views")), 6))
        .withColumn("cart_to_purchase_rate", F.round(F.col("purchases") / F.when(F.col("carts") == 0, None).otherwise(F.col("carts")), 6))
    )
    totals = grouped.agg(
        F.sum("revenue").alias("_total_revenue"),
        F.sum("purchases").alias("_total_purchases"),
    )
    return (
        grouped.crossJoin(totals)
        .withColumn("revenue_share", F.round(F.col("revenue") / F.when(F.col("_total_revenue") == 0, None).otherwise(F.col("_total_revenue")), 6))
        .withColumn("purchase_share", F.round(F.col("purchases") / F.when(F.col("_total_purchases") == 0, None).otherwise(F.col("_total_purchases")), 6))
        .withColumn("contract_version", F.lit(PORTFOLIO_CONTRACT_VERSION))
        .drop("_total_revenue", "_total_purchases")
    )


def build_category_mix(enriched: DataFrame) -> DataFrame:
    return (
        aggregate_mix(enriched, ["category_level1"])
        .select(
            "contract_version",
            "category_level1",
            "views",
            "carts",
            "purchases",
            "revenue",
            "avg_price",
            "view_to_cart_rate",
            "view_to_purchase_rate",
            "cart_to_purchase_rate",
            "revenue_share",
            "purchase_share",
        )
        .orderBy(F.desc("revenue"), F.desc("purchases"))
    )


def build_brand_mix(enriched: DataFrame) -> DataFrame:
    return (
        aggregate_mix(enriched, ["category_level1", "brand"])
        .select(
            "contract_version",
            "category_level1",
            "brand",
            "views",
            "carts",
            "purchases",
            "revenue",
            "avg_price",
            "view_to_purchase_rate",
            "revenue_share",
            "purchase_share",
        )
        .orderBy(F.desc("revenue"), F.desc("purchases"))
    )


def build_price_band_mix(enriched: DataFrame) -> DataFrame:
    return (
        aggregate_mix(enriched.filter(F.col("event_type") == "purchase"), ["category_level1", "price_band"])
        .select(
            "contract_version",
            "category_level1",
            "price_band",
            "purchases",
            "revenue",
            "avg_price",
            "revenue_share",
            "purchase_share",
        )
        .orderBy(F.desc("revenue"), F.desc("purchases"))
    )


def build_product_concentration(enriched: DataFrame, config: dict[str, Any]) -> DataFrame:
    purchases = enriched.filter(F.col("event_type") == "purchase")
    product = (
        purchases.groupBy("product_id", "category_level1", "brand")
        .agg(F.count("*").alias("purchases"), F.round(F.sum("price"), 2).alias("revenue"))
        .filter(F.col("revenue") > 0)
    )
    totals = product.agg(
        F.sum("revenue").alias("_total_revenue"),
        F.sum("purchases").alias("_total_purchases"),
    )
    scored = (
        product.crossJoin(totals)
        .withColumn("revenue_share", F.round(F.col("revenue") / F.when(F.col("_total_revenue") == 0, None).otherwise(F.col("_total_revenue")), 6))
        .withColumn("purchase_share", F.round(F.col("purchases") / F.when(F.col("_total_purchases") == 0, None).otherwise(F.col("_total_purchases")), 6))
        .withColumn("hhi_contribution", F.round(F.col("revenue_share") * F.col("revenue_share"), 8))
        .withColumn("contract_version", F.lit(PORTFOLIO_CONTRACT_VERSION))
        .drop("_total_revenue", "_total_purchases")
    )
    ranked = with_global_rank(
        scored,
        [F.desc("revenue"), F.desc("purchases")],
        limit=int(config["top_products"]),
    )
    return (
        ranked
        .select(
            "contract_version",
            "rank",
            "product_id",
            "category_level1",
            "brand",
            "purchases",
            "revenue",
            "revenue_share",
            "purchase_share",
            "hhi_contribution",
        )
        .orderBy("rank")
    )


def build_opportunities(category_mix: DataFrame, price_bands: DataFrame, config: dict[str, Any]) -> DataFrame:
    category_opportunities = (
        category_mix.withColumn(
            "opportunity_type",
            F.when((F.col("views") >= 100) & (F.coalesce(F.col("view_to_purchase_rate"), F.lit(0)) < 0.02), F.lit("traffic_conversion_gap"))
            .when(F.col("revenue_share") >= 0.35, F.lit("concentration_risk"))
            .otherwise(F.lit("portfolio_watch")),
        )
        .withColumn("entity_type", F.lit("category"))
        .withColumn("entity_id", F.col("category_level1"))
        .withColumn("price_band", F.lit(None).cast("string"))
        .withColumn("impact_score", F.round(F.col("revenue") * F.greatest(F.lit(0.02) - F.coalesce(F.col("view_to_purchase_rate"), F.lit(0)), F.lit(0.001)), 4))
        .withColumn("confidence", F.round(F.least(F.col("purchases") / F.lit(float(config["min_purchase_rows"])), F.lit(1.0)), 6))
        .withColumn("reason_codes", F.array(F.col("opportunity_type")))
        .select(
            "contract_version",
            "opportunity_type",
            "entity_type",
            "entity_id",
            "price_band",
            "impact_score",
            "confidence",
            "views",
            "purchases",
            "revenue",
            "reason_codes",
        )
    )
    band_opportunities = (
        price_bands.withColumn("opportunity_type", F.lit("price_band_mix"))
        .withColumn("entity_type", F.lit("category_price_band"))
        .withColumn("entity_id", F.col("category_level1"))
        .withColumn("impact_score", F.round(F.col("revenue") * F.col("revenue_share"), 4))
        .withColumn("confidence", F.round(F.least(F.col("purchases") / F.lit(float(config["min_purchase_rows"])), F.lit(1.0)), 6))
        .withColumn("views", F.lit(None).cast("long"))
        .withColumn("reason_codes", F.array(F.lit("price_band_revenue_pool")))
        .select(
            "contract_version",
            "opportunity_type",
            "entity_type",
            "entity_id",
            "price_band",
            "impact_score",
            "confidence",
            "views",
            "purchases",
            "revenue",
            "reason_codes",
        )
    )
    return category_opportunities.unionByName(band_opportunities).orderBy(F.desc("impact_score"), F.desc("confidence"))


def build_quality(enriched: DataFrame, price_bands: DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    agg = enriched.agg(
        F.count("*").alias("rows"),
        F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchase_rows"),
        F.sum(F.when((F.col("event_type") == "purchase") & F.col("price").isNotNull() & (F.col("price") >= 0), 1).otherwise(0)).alias("valid_price_purchases"),
        F.countDistinct("dt").alias("history_days"),
        F.countDistinct("category_level1").alias("category_count"),
        F.countDistinct("brand").alias("brand_count"),
    ).collect()[0].asDict()
    purchase_rows = int(agg.get("purchase_rows") or 0)
    valid_price_rate = round((int(agg.get("valid_price_purchases") or 0) / purchase_rows), 6) if purchase_rows else 0.0
    price_band_count = (
        price_bands.where(F.col("price_band").isNotNull() & (F.col("price_band") != "unknown"))
        .select("price_band")
        .distinct()
        .count()
    )
    checks = [
        {"name": "purchase_rows", "actual": purchase_rows, "operator": ">=", "expected": int(config["min_purchase_rows"]), "passed": purchase_rows >= int(config["min_purchase_rows"])},
        {"name": "history_days", "actual": int(agg.get("history_days") or 0), "operator": ">=", "expected": int(config["min_history_days"]), "passed": int(agg.get("history_days") or 0) >= int(config["min_history_days"])},
        {"name": "valid_price_purchase_rate", "actual": valid_price_rate, "operator": ">=", "expected": float(config["min_valid_price_purchase_rate"]), "passed": valid_price_rate >= float(config["min_valid_price_purchase_rate"])},
        {"name": "price_band_count", "actual": price_band_count, "operator": ">=", "expected": 2, "passed": price_band_count >= 2},
    ]
    warnings = [check["name"] for check in checks if not check["passed"]]
    return {
        "contract_version": PORTFOLIO_CONTRACT_VERSION,
        "quality_status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "passed": all(check["passed"] for check in checks),
        "rows": int(agg.get("rows") or 0),
        "purchase_rows": purchase_rows,
        "history_days": int(agg.get("history_days") or 0),
        "category_count": int(agg.get("category_count") or 0),
        "brand_count": int(agg.get("brand_count") or 0),
        "valid_price_purchase_rate": valid_price_rate,
        "price_band_count": price_band_count,
        "warnings": warnings,
        "checks": checks,
    }


def build_summary(
    category_mix: DataFrame,
    product_concentration: DataFrame,
    opportunities: DataFrame,
    category_rows: list[dict[str, Any]],
    concentration_rows: list[dict[str, Any]],
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    totals = category_mix.agg(
        F.round(F.sum("revenue"), 2).alias("total_revenue"),
        F.sum("purchases").alias("total_purchases"),
    ).first()
    top_category = category_rows[0] if category_rows else None
    top_product_share = float(concentration_rows[0].get("revenue_share") or 0) if concentration_rows else 0.0
    hhi_row = product_concentration.agg(F.round(F.sum("hhi_contribution"), 8).alias("hhi")).first()
    return {
        "contract_version": PORTFOLIO_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "quality_status": quality["quality_status"],
        "total_revenue": float(totals["total_revenue"] or 0),
        "total_purchases": int(totals["total_purchases"] or 0),
        "category_count": quality["category_count"],
        "brand_count": quality["brand_count"],
        "price_band_count": quality["price_band_count"],
        "warnings": quality["warnings"],
        "top_category": top_category,
        "top_product_revenue_share": top_product_share,
        "product_revenue_hhi": float(hhi_row["hhi"] or 0),
        "opportunity_count": opportunities.count(),
        "recommended_action": "Use portfolio mix, concentration, and price-band gaps to prioritize merchandising and recommendation reviews.",
        "config": {
            "min_purchase_rows": int(config["min_purchase_rows"]),
            "min_history_days": int(config["min_history_days"]),
        },
    }


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
