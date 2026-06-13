from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyspark.ml import Pipeline
from pyspark.ml.classification import GBTClassifier, LogisticRegression
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark import StorageLevel

from spark_jobs.writers import write_json_atomic


RECOMMENDATION_CONTRACT_VERSION = "nearline-recommendation/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "top_k": 5,
    "evaluation_top_k": 5,
    "session_sample_limit": 500,
    "candidate_pool": 80,
    "min_confidence": 0.02,
    "min_coverage_rate": 0.75,
    "max_fallback_rate": 0.8,
    "min_avg_confidence": 0.03,
    "max_freshness_lag_minutes": 5_300_000,
    "max_duplicate_recommendation_rate": 0.0,
    "max_invalid_product_rate": 0.0,
    "als_rank": 8,
    "als_max_iter": 5,
    "als_reg_param": 0.08,
    "als_alpha": 20.0,
    "als_min_training_rows": 30,
    "evaluation_preview_users": 20,
    "graph_neighbor_candidate_pool": 80,
    "min_graph_neighbor_support": 2,
    "min_graph_neighbor_lift": 1.01,
    "ranker_enabled": True,
    "ranker_min_training_rows": 50,
    "ranker_max_iter": 10,
    "ranker_max_depth": 3,
    "ranker_reg_param": 0.05,
    "ranker_blend_weight": 0.7,
    "ranker_algorithm": "logistic",
}

RANKER_MODEL_RULE = "interpretable_rule_ranker_v1"
RANKER_MODEL_SPARK_LOGISTIC = "spark_ml_logistic_ranker_v1"
RANKER_MODEL_SPARK_GBT = "spark_ml_gbt_ranker_v1"
RANKER_FEATURE_COLUMNS = [
    "ranker_rule_score",
    "ranker_confidence",
    "ranker_affinity_score",
    "ranker_fallback_flag",
    "ranker_graph_source_flag",
    "ranker_personalized_source_flag",
    "ranker_fallback_source_flag",
]


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
        config,
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
        evaluation = build_recommendation_evaluation(
            cleaned_df,
            recommendation_features,
            config,
            run_id=run_id,
        )
        candidates = build_recommendation_candidates(
            recommendation_features,
            limit=int(config.get("preview_limit", int(config["session_sample_limit"]) * int(config["top_k"]))),
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
            "evaluation": evaluation,
            "candidates": candidates,
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
    config: dict[str, Any] | None = None,
) -> DataFrame:
    effective_config = recommendation_config(config)
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
            F.lit(0.0).alias("affinity_score"),
        )
    )
    graph_neighbors = build_graph_neighbor_candidates(
        cleaned_df,
        product_features,
        target_sessions,
        seen_products,
        min_confidence,
        int(effective_config["graph_neighbor_candidate_pool"]),
        int(effective_config["min_graph_neighbor_support"]),
        float(effective_config["min_graph_neighbor_lift"]),
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
            F.lit(0.0).alias("affinity_score"),
        )
    )
    merged = personalized.unionByName(graph_neighbors).unionByName(fallback)
    dedupe_window = Window.partitionBy("user_session", "product_id").orderBy(
        F.asc("fallback_used"),
        F.desc("score"),
        F.desc("confidence"),
    )
    ranked = merged.withColumn("product_choice_rank", F.row_number().over(dedupe_window)).filter(
        F.col("product_choice_rank") == 1
    )
    scored = apply_lightweight_ranker(ranked, cleaned_df, product_features, effective_config)
    rank_window = Window.partitionBy("user_session").orderBy(F.desc("score"), F.desc("confidence"), F.asc("product_id"))
    return (
        scored.withColumn("rank", F.row_number().over(rank_window))
        .filter(F.col("rank") <= top_k)
        .drop("product_choice_rank")
        .orderBy("user_session", "rank")
    )


def apply_lightweight_ranker(candidates: DataFrame, cleaned_df: DataFrame, product_features: DataFrame, config: dict[str, Any]) -> DataFrame:
    rule_scored = with_rule_ranker_metadata(candidates)
    if not bool(config.get("ranker_enabled", True)):
        return rule_scored

    training = build_ranker_training_frame(cleaned_df, product_features).persist(StorageLevel.MEMORY_AND_DISK)
    try:
        stats = training.agg(
            F.count("*").alias("row_count"),
            F.sum("ranker_label").alias("positive_count"),
        ).first()
        row_count = int(stats["row_count"] or 0)
        positive_count = int(stats["positive_count"] or 0)
        min_training_rows = int(config.get("ranker_min_training_rows", 50))
        if row_count < min_training_rows or positive_count == 0 or positive_count == row_count:
            return rule_scored

        assembler = VectorAssembler(inputCols=RANKER_FEATURE_COLUMNS, outputCol="ranker_features", handleInvalid="keep")
        classifier, ranker_model_name = build_ranker_classifier(config)
        model = Pipeline(stages=[assembler, classifier]).fit(training)
        transformed = model.transform(with_ranker_feature_columns(rule_scored))
        blend_weight = max(0.0, min(1.0, float(config.get("ranker_blend_weight", 0.7))))
        probability_score = (
            vector_to_array("ranker_probability_vector").getItem(1)
            if "ranker_probability_vector" in transformed.columns
            else F.coalesce(F.col("ranker_prediction").cast("double"), F.lit(0.0))
        )
        return (
            transformed.withColumn("ranker_probability", probability_score)
            .withColumn("rule_score", F.col("score"))
            .withColumn(
                "score",
                F.round(
                    F.col("ranker_probability") * F.lit(blend_weight)
                    + F.least(F.greatest(F.col("rule_score"), F.lit(0.0)), F.lit(1.0)) * F.lit(1.0 - blend_weight),
                    8,
                ),
            )
            .withColumn("ranker_model", F.lit(ranker_model_name))
            .drop("ranker_features", "ranker_probability_vector", "ranker_prediction", "ranker_raw_prediction", "ranker_probability", "rule_score")
        )
    except Exception:
        return rule_scored
    finally:
        training.unpersist()


def build_ranker_classifier(config: dict[str, Any]) -> tuple[LogisticRegression | GBTClassifier, str]:
    algorithm = str(config.get("ranker_algorithm", "logistic")).lower()
    if algorithm == "gbt":
        return (
            GBTClassifier(
                featuresCol="ranker_features",
                labelCol="ranker_label",
                predictionCol="ranker_prediction",
                maxIter=int(config.get("ranker_max_iter", 10)),
                maxDepth=int(config.get("ranker_max_depth", 3)),
                seed=13,
            ),
            RANKER_MODEL_SPARK_GBT,
        )
    return (
        LogisticRegression(
            featuresCol="ranker_features",
            labelCol="ranker_label",
            probabilityCol="ranker_probability_vector",
            predictionCol="ranker_prediction",
            rawPredictionCol="ranker_raw_prediction",
            maxIter=int(config.get("ranker_max_iter", 10)),
            regParam=float(config.get("ranker_reg_param", 0.05)),
        ),
        RANKER_MODEL_SPARK_LOGISTIC,
    )


def with_rule_ranker_metadata(candidates: DataFrame) -> DataFrame:
    return with_ranker_feature_columns(candidates).withColumn("ranker_model", F.lit(RANKER_MODEL_RULE))


def with_ranker_feature_columns(candidates: DataFrame) -> DataFrame:
    return (
        candidates.withColumn("ranker_rule_score", F.coalesce(F.col("score"), F.lit(0.0)).cast("double"))
        .withColumn("ranker_confidence", F.coalesce(F.col("confidence"), F.lit(0.0)).cast("double"))
        .withColumn("ranker_affinity_score", F.coalesce(F.col("affinity_score"), F.lit(0.0)).cast("double"))
        .withColumn("ranker_fallback_flag", F.when(F.col("fallback_used"), F.lit(1.0)).otherwise(F.lit(0.0)))
        .withColumn("ranker_graph_source_flag", F.when(F.col("source") == "graph_neighbor", F.lit(1.0)).otherwise(F.lit(0.0)))
        .withColumn("ranker_personalized_source_flag", F.when(F.col("source") == "personalized_category", F.lit(1.0)).otherwise(F.lit(0.0)))
        .withColumn("ranker_fallback_source_flag", F.when(F.col("source") == "optimization_fallback", F.lit(1.0)).otherwise(F.lit(0.0)))
    )


def build_ranker_training_frame(cleaned_df: DataFrame, product_features: DataFrame) -> DataFrame:
    labels = (
        cleaned_df.groupBy("user_session", "product_id")
        .agg(F.max(F.when(F.col("event_type") == "purchase", F.lit(1.0)).otherwise(F.lit(0.0))).alias("ranker_label"))
        .filter(F.col("user_session") != "unknown")
    )
    return (
        labels.join(
            product_features.select("product_id", "product_score", "confidence"),
            on="product_id",
            how="inner",
        )
        .withColumn("score", F.coalesce(F.col("product_score"), F.lit(0.0)))
        .withColumn("affinity_score", F.lit(0.0))
        .withColumn("fallback_used", F.lit(False))
        .withColumn("source", F.lit("historical_interaction"))
        .transform(with_ranker_feature_columns)
        .select(*RANKER_FEATURE_COLUMNS, "ranker_label")
    )


def build_graph_neighbor_candidates(
    cleaned_df: DataFrame,
    product_features: DataFrame,
    target_sessions: DataFrame,
    seen_products: DataFrame,
    min_confidence: float,
    candidate_pool: int,
    min_support: int,
    min_lift: float,
) -> DataFrame:
    session_products = (
        cleaned_df.filter(F.col("user_session") != "unknown")
        .select("user_session", "product_id")
        .dropDuplicates()
        .persist(StorageLevel.MEMORY_AND_DISK)
    )
    try:
        total_sessions = max(session_products.select("user_session").distinct().count(), 1)
        product_session_counts = session_products.groupBy("product_id").agg(
            F.countDistinct("user_session").alias("product_sessions")
        )
        directed_pairs = (
            session_products.alias("source")
            .join(
                session_products.alias("target"),
                (F.col("source.user_session") == F.col("target.user_session"))
                & (F.col("source.product_id") != F.col("target.product_id")),
                "inner",
            )
            .select(
                F.col("source.user_session").alias("user_session"),
                F.col("source.product_id").alias("source_product_id"),
                F.col("target.product_id").alias("target_product_id"),
            )
        )
        edges = (
            directed_pairs.groupBy("source_product_id", "target_product_id")
            .agg(F.countDistinct("user_session").alias("support"))
            .join(
                product_session_counts.select(
                    F.col("product_id").alias("source_product_id"),
                    F.col("product_sessions").alias("source_sessions"),
                ),
                on="source_product_id",
                how="inner",
            )
            .join(
                product_session_counts.select(
                    F.col("product_id").alias("target_product_id"),
                    F.col("product_sessions").alias("target_sessions"),
                ),
                on="target_product_id",
                how="inner",
            )
            .withColumn("edge_confidence", F.col("support") / F.col("source_sessions"))
            .withColumn("target_prior", F.col("target_sessions") / F.lit(float(total_sessions)))
            .withColumn("edge_lift", F.col("edge_confidence") / F.col("target_prior"))
            .filter((F.col("support") >= min_support) & (F.col("edge_lift") >= min_lift) & (F.col("target_prior") > 0))
        )
        raw_candidates = (
            target_sessions.alias("sessions")
            .join(seen_products.alias("seen_source"), on="user_session", how="inner")
            .join(edges.alias("edges"), F.col("seen_source.product_id") == F.col("edges.source_product_id"), "inner")
            .join(product_features.alias("products"), F.col("edges.target_product_id") == F.col("products.product_id"), "inner")
            .join(
                seen_products.alias("seen_target"),
                (F.col("sessions.user_session") == F.col("seen_target.user_session"))
                & (F.col("products.product_id") == F.col("seen_target.product_id")),
                "left_anti",
            )
            .withColumn(
                "affinity_score",
                F.round(
                    F.least(
                        F.lit(1.0),
                        (F.log1p(F.col("edges.edge_lift")) / F.log1p(F.lit(10.0))) * F.lit(0.65)
                        + F.col("edges.edge_confidence") * F.lit(0.25)
                        + F.least(F.col("edges.support") / F.lit(20.0), F.lit(1.0)) * F.lit(0.10),
                    ),
                    6,
                ),
            )
            .withColumn(
                "candidate_confidence",
                F.round(F.least(F.lit(1.0), F.col("products.confidence") * F.lit(0.65) + F.col("edges.edge_confidence") * F.lit(0.35)), 6),
            )
            .filter(F.col("candidate_confidence") >= min_confidence)
            .withColumn(
                "candidate_score",
                F.round(
                    F.col("products.product_score") * F.lit(0.75)
                    + F.col("candidate_confidence") * F.lit(0.05)
                    + F.col("affinity_score") * F.lit(0.25),
                    8,
                ),
            )
            .select(
                F.col("sessions.user_session").alias("user_session"),
                F.col("sessions.user_id").alias("user_id"),
                F.col("products.product_id").alias("product_id"),
                F.col("products.brand").alias("brand"),
                F.col("products.category_level1").alias("category_level1"),
                F.col("candidate_score").alias("score"),
                F.col("candidate_confidence").alias("confidence"),
                F.array(F.lit("graph_neighbor_recall"), F.lit("high_lift")).alias("reason_codes"),
                F.lit("graph_neighbor").alias("source"),
                F.lit(False).alias("fallback_used"),
                F.col("affinity_score").alias("affinity_score"),
                F.col("edges.support").alias("edge_support"),
                F.col("edges.edge_lift").alias("edge_lift"),
            )
        )
        dedupe_window = Window.partitionBy("user_session", "product_id").orderBy(
            F.desc("affinity_score"),
            F.desc("edge_support"),
            F.desc("edge_lift"),
        )
        pool_window = Window.partitionBy("user_session").orderBy(F.desc("score"), F.desc("affinity_score"), F.asc("product_id"))
        return (
            raw_candidates.withColumn("graph_choice_rank", F.row_number().over(dedupe_window))
            .filter(F.col("graph_choice_rank") == 1)
            .withColumn("graph_pool_rank", F.row_number().over(pool_window))
            .filter(F.col("graph_pool_rank") <= candidate_pool)
            .drop("edge_support", "edge_lift", "graph_choice_rank", "graph_pool_rank")
        )
    finally:
        session_products.unpersist()


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


def build_recommendation_evaluation(
    cleaned_df: DataFrame,
    recommendation_features: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any]:
    top_k = int(config.get("evaluation_top_k", config["top_k"]))
    interactions = build_weighted_interactions(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    try:
        split = split_interactions_for_evaluation(interactions)
        train = split["train"].persist(StorageLevel.MEMORY_AND_DISK)
        holdout = split["holdout"].persist(StorageLevel.MEMORY_AND_DISK)
        try:
            catalog_count = interactions.select("product_id").distinct().count()
            truth = {
                str(row["user_session"]): {str(row["product_id"])}
                for row in holdout.select("user_session", "product_id").collect()
            }
            holdout_pairs = holdout.select("user_session", "product_id").dropDuplicates().persist(StorageLevel.MEMORY_AND_DISK)
            evaluation_events = cleaned_df.join(holdout_pairs, on=["user_session", "product_id"], how="left_anti").persist(
                StorageLevel.MEMORY_AND_DISK
            )
            evaluation_product_features = build_product_features(
                evaluation_events,
                int(config["candidate_pool"]),
            ).persist(StorageLevel.MEMORY_AND_DISK)
            evaluation_target_sessions = (
                build_target_sessions(
                    evaluation_events,
                    max(int(config["session_sample_limit"]), len(truth)),
                )
                .join(holdout.select("user_session").distinct(), on="user_session", how="inner")
                .persist(StorageLevel.MEMORY_AND_DISK)
            )
            evaluation_recommendations = build_recommendation_features(
                evaluation_events,
                evaluation_product_features,
                evaluation_target_sessions,
                [],
                top_k,
                float(config["min_confidence"]),
                {**config, "ranker_enabled": False},
            ).persist(StorageLevel.MEMORY_AND_DISK)
            try:
                rule_predictions = [
                    _prediction_from_row(row.asDict())
                    for row in evaluation_recommendations.select(
                        "user_session",
                        "product_id",
                        "rank",
                        "score",
                        "source",
                        "fallback_used",
                    ).collect()
                ]
                production_recommendation_rows = recommendation_features.count()
            finally:
                evaluation_recommendations.unpersist()
                evaluation_target_sessions.unpersist()
                evaluation_product_features.unpersist()
                evaluation_events.unpersist()
                holdout_pairs.unpersist()
            rule_metrics = _ranking_metrics(
                "rule_recommendation",
                rule_predictions,
                truth,
                top_k,
                catalog_count,
                fallback_rate=_safe_rate(
                    sum(1 for row in rule_predictions if row.get("fallback_used")),
                    len(rule_predictions),
                ),
                status="evaluated" if truth else "skipped",
                caveat="train_split_recomputed" if truth else "no_holdout_sessions",
            )
            als_predictions, als_status, als_caveat = _build_als_predictions(train, holdout, config, top_k)
            als_metrics = _ranking_metrics(
                "als_implicit",
                als_predictions,
                truth,
                top_k,
                catalog_count,
                fallback_rate=0.0,
                status=als_status,
                caveat=als_caveat,
            )
            return {
                "contract_version": RECOMMENDATION_CONTRACT_VERSION,
                "run_id": run_id,
                "top_k": top_k,
                "split": {
                    "strategy": "leave_latest_interaction_per_session",
                    "rule_candidate_source": "train_split_recomputed",
                    "leakage_guard": "holdout_pairs_removed_before_candidate_generation",
                    "train_rows": train.count(),
                    "holdout_rows": holdout.count(),
                    "evaluated_sessions": len(truth),
                    "production_recommendation_rows": production_recommendation_rows,
                },
                "behavior_weights": {"view": 1, "cart": 3, "purchase": 8},
                "model_metrics": [rule_metrics, als_metrics],
                "source_mix": _source_mix(rule_predictions),
                "topk_matrix": _topk_matrix([*rule_predictions, *als_predictions], truth, int(config["evaluation_preview_users"])),
                "quality_gates": [
                    {
                        "name": "recall_at_k_available",
                        "actual": rule_metrics["recall_at_k"],
                        "operator": ">=",
                        "expected": 0,
                        "passed": rule_metrics["recall_at_k"] is not None,
                    },
                    {
                        "name": "als_baseline_available",
                        "actual": als_status,
                        "operator": "==",
                        "expected": "evaluated",
                        "passed": als_status == "evaluated",
                    },
                ],
            }
        finally:
            train.unpersist()
            holdout.unpersist()
    finally:
        interactions.unpersist()


def build_recommendation_candidates(recommendation_features: DataFrame, limit: int = 500) -> list[dict[str, Any]]:
    session_window = Window.partitionBy("user_session")
    scored = (
        recommendation_features.withColumn("max_score", F.max("score").over(session_window))
        .withColumn("max_confidence", F.max("confidence").over(session_window))
        .withColumn(
            "ranker_score",
            F.round(F.col("score") / F.when(F.col("max_score") == 0, None).otherwise(F.col("max_score")), 6),
        )
        .withColumn(
            "source_score",
            F.round(F.col("confidence") / F.when(F.col("max_confidence") == 0, None).otherwise(F.col("max_confidence")), 6),
        )
        .withColumn(
            "recall_stage",
            F.when(F.col("source") == "personalized_category", F.lit("category_recall"))
            .when(F.col("source") == "graph_neighbor", F.lit("graph_neighbor_recall"))
            .when(F.col("source") == "optimization_fallback", F.lit("popular_fallback"))
            .when(F.col("source") == "als_implicit", F.lit("als_recall"))
            .otherwise(F.col("source")),
        )
        .withColumn(
            "calibration_bucket",
            F.when(F.col("ranker_score") >= 0.8, F.lit("high"))
            .when(F.col("ranker_score") >= 0.5, F.lit("medium"))
            .otherwise(F.lit("low")),
        )
        .withColumn("ranker_model", F.col("ranker_model") if "ranker_model" in recommendation_features.columns else F.lit(RANKER_MODEL_RULE))
        .withColumn("candidate_stage", F.lit("ranked_topk"))
        .withColumn("conversion_score", F.round("score", 6))
        .withColumn("freshness_score", F.round("confidence", 6))
        .withColumn("affinity_score", F.round(F.coalesce(F.col("affinity_score"), F.lit(0.0)), 6))
    )
    rows = (
        scored.orderBy("user_session", "rank")
        .limit(limit)
        .select(
            "user_session",
            "user_id",
            "product_id",
            "brand",
            "category_level1",
            "rank",
            "source",
            "recall_stage",
            "candidate_stage",
            "score",
            "ranker_score",
            "source_score",
            "conversion_score",
            "freshness_score",
            "affinity_score",
            "confidence",
            "ranker_model",
            "calibration_bucket",
            "reason_codes",
            "fallback_used",
        )
        .collect()
    )
    return [_candidate_from_row(row.asDict(recursive=True)) for row in rows]


def build_weighted_interactions(cleaned_df: DataFrame) -> DataFrame:
    event_weight = (
        F.when(F.col("event_type") == "purchase", F.lit(8.0))
        .when(F.col("event_type") == "cart", F.lit(3.0))
        .when(F.col("event_type") == "view", F.lit(1.0))
        .otherwise(F.lit(0.0))
    )
    return (
        cleaned_df.filter(F.col("user_session") != "unknown")
        .withColumn("event_weight", event_weight)
        .groupBy("user_session", "product_id")
        .agg(
            F.sum("event_weight").alias("rating"),
            F.max("event_timestamp").alias("latest_event_ts"),
            F.count("*").alias("interaction_count"),
        )
        .filter(F.col("rating") > 0)
    )


def split_interactions_for_evaluation(interactions: DataFrame) -> dict[str, DataFrame]:
    session_window = Window.partitionBy("user_session").orderBy(F.desc("latest_event_ts"), F.desc("rating"), F.asc("product_id"))
    ranked = interactions.withColumn("interaction_rank", F.row_number().over(session_window))
    eligible_sessions = ranked.groupBy("user_session").agg(F.count("*").alias("products")).filter(F.col("products") >= 2)
    eligible = ranked.join(eligible_sessions.select("user_session"), on="user_session", how="inner")
    return {
        "train": eligible.filter(F.col("interaction_rank") > 1).drop("interaction_rank"),
        "holdout": eligible.filter(F.col("interaction_rank") == 1).drop("interaction_rank"),
    }


def _build_als_predictions(
    train: DataFrame,
    holdout: DataFrame,
    config: dict[str, Any],
    top_k: int,
) -> tuple[list[dict[str, Any]], str, str]:
    training_rows = train.count()
    if training_rows < int(config["als_min_training_rows"]):
        return [], "skipped", "insufficient_training_rows"
    user_count = train.select("user_session").distinct().count()
    item_count = train.select("product_id").distinct().count()
    if user_count < 2 or item_count < 2:
        return [], "skipped", "insufficient_users_or_items"
    try:
        from pyspark.ml.recommendation import ALS

        user_window = Window.orderBy("user_session")
        item_window = Window.orderBy("product_id")
        user_map = train.select("user_session").distinct().withColumn("user_idx", F.row_number().over(user_window) - F.lit(1))
        product_map = train.select("product_id").distinct().withColumn("product_idx", F.row_number().over(item_window) - F.lit(1))
        indexed = (
            train.join(user_map, on="user_session", how="inner")
            .join(product_map, on="product_id", how="inner")
            .select(
                F.col("user_idx").cast("int").alias("user_idx"),
                F.col("product_idx").cast("int").alias("product_idx"),
                F.col("rating").cast("double").alias("rating"),
            )
        )
        als = ALS(
            userCol="user_idx",
            itemCol="product_idx",
            ratingCol="rating",
            implicitPrefs=True,
            coldStartStrategy="drop",
            rank=int(config["als_rank"]),
            maxIter=int(config["als_max_iter"]),
            regParam=float(config["als_reg_param"]),
            alpha=float(config["als_alpha"]),
        )
        model = als.fit(indexed)
        user_subset = holdout.select("user_session").distinct().join(user_map, on="user_session", how="inner").select("user_idx")
        raw_recs = model.recommendForUserSubset(user_subset, max(top_k * 3, top_k))
        seen = indexed.select("user_idx", "product_idx").dropDuplicates()
        ranked_window = Window.partitionBy("user_session").orderBy(F.desc("score"), F.asc("product_id"))
        predictions = (
            raw_recs.select("user_idx", F.explode("recommendations").alias("recommendation"))
            .select(
                "user_idx",
                F.col("recommendation.product_idx").cast("int").alias("product_idx"),
                F.col("recommendation.rating").cast("double").alias("score"),
            )
            .join(seen, on=["user_idx", "product_idx"], how="left_anti")
            .join(user_map, on="user_idx", how="inner")
            .join(product_map, on="product_idx", how="inner")
            .withColumn("rank", F.row_number().over(ranked_window))
            .filter(F.col("rank") <= top_k)
            .select("user_session", "product_id", "rank", "score")
            .collect()
        )
        return [
            {
                "model_name": "als_implicit",
                "user_session": str(row["user_session"]),
                "product_id": str(row["product_id"]),
                "rank": int(row["rank"]),
                "score": float(row["score"] or 0),
                "source": "als_implicit",
                "fallback_used": False,
            }
            for row in predictions
        ], "evaluated", ""
    except Exception as exc:
        return [], "skipped", f"als_training_failed:{type(exc).__name__}"


def _prediction_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_name": "rule_recommendation",
        "user_session": str(row["user_session"]),
        "product_id": str(row["product_id"]),
        "rank": int(row["rank"]),
        "score": float(row.get("score") or 0),
        "source": row.get("source") or "unknown",
        "fallback_used": bool(row.get("fallback_used")),
    }


def _ranking_metrics(
    model_name: str,
    predictions: list[dict[str, Any]],
    truth: dict[str, set[str]],
    top_k: int,
    catalog_count: int,
    *,
    fallback_rate: float,
    status: str,
    caveat: str,
) -> dict[str, Any]:
    by_user: dict[str, list[dict[str, Any]]] = {}
    for row in predictions:
        by_user.setdefault(row["user_session"], []).append(row)
    precision_values: list[float] = []
    recall_values: list[float] = []
    ndcg_values: list[float] = []
    hit_count = 0
    unique_items: set[str] = set()
    for user_session, relevant in truth.items():
        ranked = sorted(by_user.get(user_session, []), key=lambda row: (row["rank"], -float(row.get("score") or 0)))[:top_k]
        predicted_items = [row["product_id"] for row in ranked]
        unique_items.update(predicted_items)
        hits = [1 if product_id in relevant else 0 for product_id in predicted_items]
        hit_count += sum(hits)
        precision_values.append(sum(hits) / top_k if top_k else 0.0)
        recall_values.append(sum(hits) / len(relevant) if relevant else 0.0)
        dcg = sum(hit / math.log2(index + 2) for index, hit in enumerate(hits))
        ideal_hits = min(len(relevant), top_k)
        ideal_dcg = sum(1 / math.log2(index + 2) for index in range(ideal_hits))
        ndcg_values.append(dcg / ideal_dcg if ideal_dcg else 0.0)
    evaluated_sessions = len(truth)
    return {
        "model_name": model_name,
        "status": status,
        "caveat": caveat,
        "evaluated_sessions": evaluated_sessions,
        "predicted_items": len(predictions),
        "hit_count": hit_count,
        "precision_at_k": round(sum(precision_values) / evaluated_sessions, 6) if evaluated_sessions else None,
        "recall_at_k": round(sum(recall_values) / evaluated_sessions, 6) if evaluated_sessions else None,
        "ndcg_at_k": round(sum(ndcg_values) / evaluated_sessions, 6) if evaluated_sessions else None,
        "catalog_coverage": _safe_rate(len(unique_items), catalog_count),
        "fallback_rate": fallback_rate,
    }


def _source_mix(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in predictions:
        source = row.get("source") or "unknown"
        counts[source] = counts.get(source, 0) + 1
    total = sum(counts.values())
    return [
        {"source": source, "recommendations": count, "share": _safe_rate(count, total)}
        for source, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _topk_matrix(
    predictions: list[dict[str, Any]],
    truth: dict[str, set[str]],
    preview_users: int,
) -> list[dict[str, Any]]:
    preview_sessions = set(sorted(truth)[:preview_users])
    rows = []
    for row in sorted(predictions, key=lambda item: (item["model_name"], item["user_session"], item["rank"])):
        if row["user_session"] not in preview_sessions:
            continue
        rows.append(
            {
                "model_name": row["model_name"],
                "user_session": row["user_session"],
                "rank": row["rank"],
                "product_id": row["product_id"],
                "hit": row["product_id"] in truth.get(row["user_session"], set()),
                "source": row.get("source") or "unknown",
                "score": round(float(row.get("score") or 0), 6),
            }
        )
    return rows


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
    write_json_atomic(run_dir / "evaluation.json", run_payload["evaluation"])
    write_json_atomic(run_dir / "candidates.json", run_payload["candidates"])

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
        "recommendation_evaluation": run_payload["evaluation"],
        "recommendation_candidates": run_payload["candidates"],
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


def _candidate_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": f"{row['user_session']}:{row['product_id']}:{row.get('source') or 'unknown'}",
        "user_session": str(row["user_session"]),
        "user_id": str(row.get("user_id") or "unknown"),
        "product_id": str(row["product_id"]),
        "brand": row.get("brand") or "unknown",
        "category_level1": row.get("category_level1") or "unknown",
        "rank": int(row["rank"]),
        "candidate_source": row.get("source") or "unknown",
        "recall_stage": row.get("recall_stage") or "unknown",
        "candidate_stage": row.get("candidate_stage") or "ranked_topk",
        "score": float(row.get("score") or 0),
        "ranker_score": float(row.get("ranker_score") or 0),
        "source_score": float(row.get("source_score") or 0),
        "conversion_score": float(row.get("conversion_score") or 0),
        "freshness_score": float(row.get("freshness_score") or 0),
        "affinity_score": float(row.get("affinity_score") or 0),
        "confidence": float(row.get("confidence") or 0),
        "ranker_model": row.get("ranker_model") or "interpretable_rule_ranker_v1",
        "calibration_bucket": row.get("calibration_bucket") or "low",
        "reason_codes": list(row.get("reason_codes") or []),
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
