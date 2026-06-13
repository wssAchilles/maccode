from __future__ import annotations

from typing import Any

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


AFFINITY_CONTRACT_VERSION = "product-affinity-graph/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "preview_limit": 120,
    "top_nodes": 120,
    "max_edges": 200,
    "min_support": 3,
    "max_pair_products_per_session": 20,
    "max_pair_rows_per_input_row": 20,
    "max_pair_rows_per_product_session": 20,
    "min_eligible_sessions": 10,
}

NODE_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("entity_id", T.StringType()),
        T.StructField("entity_type", T.StringType()),
        T.StructField("entity_label", T.StringType()),
        T.StructField("brand", T.StringType()),
        T.StructField("category_level1", T.StringType()),
        T.StructField("views", T.LongType()),
        T.StructField("carts", T.LongType()),
        T.StructField("purchases", T.LongType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("degree", T.LongType()),
        T.StructField("weighted_degree", T.DoubleType()),
        T.StructField("community_id", T.StringType()),
    ]
)

EDGE_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("source_id", T.StringType()),
        T.StructField("target_id", T.StringType()),
        T.StructField("source_type", T.StringType()),
        T.StructField("target_type", T.StringType()),
        T.StructField("source_label", T.StringType()),
        T.StructField("target_label", T.StringType()),
        T.StructField("source_brand", T.StringType()),
        T.StructField("target_brand", T.StringType()),
        T.StructField("source_category", T.StringType()),
        T.StructField("target_category", T.StringType()),
        T.StructField("relation_type", T.StringType()),
        T.StructField("support", T.LongType()),
        T.StructField("confidence", T.DoubleType()),
        T.StructField("lift", T.DoubleType()),
        T.StructField("jaccard", T.DoubleType()),
        T.StructField("revenue_overlap", T.DoubleType()),
        T.StructField("sample_sessions", T.LongType()),
        T.StructField("quality_status", T.StringType()),
    ]
)

OPPORTUNITY_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("opportunity_id", T.StringType()),
        T.StructField("type", T.StringType()),
        T.StructField("primary_entity", T.StringType()),
        T.StructField("primary_label", T.StringType()),
        T.StructField("related_entity", T.StringType()),
        T.StructField("related_label", T.StringType()),
        T.StructField("reason_codes", T.ArrayType(T.StringType())),
        T.StructField("estimated_revenue_pool", T.DoubleType()),
        T.StructField("confidence", T.DoubleType()),
        T.StructField("lift", T.DoubleType()),
        T.StructField("support", T.LongType()),
        T.StructField("risk_level", T.StringType()),
        T.StructField("action", T.StringType()),
    ]
)

COMMUNITY_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("community_id", T.StringType()),
        T.StructField("category_level1", T.StringType()),
        T.StructField("node_count", T.LongType()),
        T.StructField("edge_count", T.LongType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("top_entities", T.ArrayType(T.StringType())),
        T.StructField("recommended_action", T.StringType()),
    ]
)

CENTRALITY_SCHEMA = T.StructType(
    [
        T.StructField("contract_version", T.StringType()),
        T.StructField("entity_id", T.StringType()),
        T.StructField("entity_label", T.StringType()),
        T.StructField("brand", T.StringType()),
        T.StructField("category_level1", T.StringType()),
        T.StructField("community_id", T.StringType()),
        T.StructField("degree", T.LongType()),
        T.StructField("weighted_degree", T.DoubleType()),
        T.StructField("normalized_weighted_degree", T.DoubleType()),
        T.StructField("pagerank_score", T.DoubleType()),
        T.StructField("centrality_score", T.DoubleType()),
        T.StructField("community_size", T.LongType()),
        T.StructField("community_revenue", T.DoubleType()),
        T.StructField("revenue", T.DoubleType()),
        T.StructField("views", T.LongType()),
        T.StructField("purchases", T.LongType()),
    ]
)


def affinity_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_affinity_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    product_sessions = build_product_sessions(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    node_base = build_node_base(product_sessions, int(config["top_nodes"])).persist(StorageLevel.MEMORY_AND_DISK)
    top_product_ids = node_base.select(F.col("entity_id").alias("product_id")).distinct()
    pair_product_sessions = product_sessions.join(top_product_ids, "product_id", "inner").persist(StorageLevel.MEMORY_AND_DISK)
    eligible_sessions = build_eligible_sessions(pair_product_sessions, config).persist(StorageLevel.MEMORY_AND_DISK)
    pair_base = build_pair_base(pair_product_sessions, eligible_sessions).persist(StorageLevel.MEMORY_AND_DISK)
    relation_edges = [
        build_relation_edges(pair_product_sessions, pair_base, "co_view", "has_view", config),
        build_relation_edges(pair_product_sessions, pair_base, "co_cart", "has_cart", config),
        build_relation_edges(pair_product_sessions, pair_base, "co_purchase", "has_purchase", config),
    ]
    edge_frame = relation_edges[0]
    for frame in relation_edges[1:]:
        edge_frame = edge_frame.unionByName(frame)
    edge_frame = edge_frame.orderBy(F.desc("lift"), F.desc("support")).limit(int(config["max_edges"])).persist(StorageLevel.MEMORY_AND_DISK)

    edge_rows = [_row_to_dict(row.asDict(recursive=True)) for row in edge_frame.collect()]
    node_rows = enrich_nodes_with_degrees([_row_to_dict(row.asDict()) for row in node_base.collect()], edge_rows)
    opportunity_rows = build_opportunities(edge_rows, int(config["preview_limit"]))
    community_rows = build_communities(node_rows, edge_rows)
    centrality_rows = build_centrality(node_rows, edge_rows, community_rows)
    quality = build_quality(pair_product_sessions, eligible_sessions, pair_base, cleaned_df.count(), edge_rows, config)
    summary = build_summary(node_rows, edge_rows, opportunity_rows, community_rows, quality, config, run_id, input_snapshot)

    spark = cleaned_df.sparkSession
    frames = {
        "nodes": _create_frame(spark, node_rows, NODE_SCHEMA),
        "edges": _create_frame(spark, edge_rows, EDGE_SCHEMA),
        "opportunities": _create_frame(spark, opportunity_rows, OPPORTUNITY_SCHEMA),
        "communities": _create_frame(spark, community_rows, COMMUNITY_SCHEMA),
        "centrality": _create_frame(spark, centrality_rows, CENTRALITY_SCHEMA),
        "session_pairs": pair_base,
    }
    preview_limit = int(config["preview_limit"])
    metrics = {
        "affinity_summary": summary,
        "affinity_nodes": node_rows[:preview_limit],
        "affinity_edges": edge_rows[:preview_limit],
        "affinity_communities": community_rows[:preview_limit],
        "affinity_opportunities": opportunity_rows[:preview_limit],
        "affinity_centrality": centrality_rows[:preview_limit],
        "affinity_quality": quality,
    }
    product_sessions.unpersist()
    node_base.unpersist()
    pair_product_sessions.unpersist()
    eligible_sessions.unpersist()
    pair_base.unpersist()
    edge_frame.unpersist()
    return frames, metrics


def build_product_sessions(cleaned_df: DataFrame) -> DataFrame:
    return (
        cleaned_df.groupBy("user_session", "product_id")
        .agg(
            F.first(F.coalesce(F.col("brand"), F.lit("unknown")), ignorenulls=True).alias("brand"),
            F.first(F.coalesce(F.col("category_level1"), F.lit("unknown")), ignorenulls=True).alias("category_level1"),
            F.max(F.when(F.col("event_type") == "view", F.lit(1)).otherwise(F.lit(0))).alias("has_view"),
            F.max(F.when(F.col("event_type") == "cart", F.lit(1)).otherwise(F.lit(0))).alias("has_cart"),
            F.max(F.when(F.col("event_type") == "purchase", F.lit(1)).otherwise(F.lit(0))).alias("has_purchase"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
            F.count(F.when(F.col("event_type") == "cart", F.lit(1))).alias("carts"),
            F.count(F.when(F.col("event_type") == "purchase", F.lit(1))).alias("purchases"),
            F.round(
                F.sum(F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))),
                2,
            ).alias("revenue"),
        )
        .withColumn("product_id", F.col("product_id").cast("string"))
    )


def build_eligible_sessions(product_sessions: DataFrame, config: dict[str, Any]) -> DataFrame:
    return (
        product_sessions.groupBy("user_session")
        .agg(F.countDistinct("product_id").alias("product_count"))
        .filter((F.col("product_count") >= 2) & (F.col("product_count") <= int(config["max_pair_products_per_session"])))
    )


def build_pair_base(product_sessions: DataFrame, eligible_sessions: DataFrame) -> DataFrame:
    left = product_sessions.join(eligible_sessions.select("user_session"), "user_session").alias("left")
    right = product_sessions.join(eligible_sessions.select("user_session"), "user_session").alias("right")
    return (
        left.join(right, F.col("left.user_session") == F.col("right.user_session"))
        .filter(F.col("left.product_id") < F.col("right.product_id"))
        .select(
            F.col("left.user_session").alias("user_session"),
            F.col("left.product_id").alias("source_id"),
            F.col("right.product_id").alias("target_id"),
            F.col("left.brand").alias("source_brand"),
            F.col("right.brand").alias("target_brand"),
            F.col("left.category_level1").alias("source_category"),
            F.col("right.category_level1").alias("target_category"),
            F.col("left.has_view").alias("source_has_view"),
            F.col("right.has_view").alias("target_has_view"),
            F.col("left.has_cart").alias("source_has_cart"),
            F.col("right.has_cart").alias("target_has_cart"),
            F.col("left.has_purchase").alias("source_has_purchase"),
            F.col("right.has_purchase").alias("target_has_purchase"),
            (F.col("left.revenue") + F.col("right.revenue")).alias("pair_revenue"),
        )
    )


def build_node_base(product_sessions: DataFrame, top_nodes: int) -> DataFrame:
    return (
        product_sessions.groupBy("product_id", "brand", "category_level1")
        .agg(
            F.sum("views").alias("views"),
            F.sum("carts").alias("carts"),
            F.sum("purchases").alias("purchases"),
            F.round(F.sum("revenue"), 2).alias("revenue"),
        )
        .orderBy(F.desc("revenue"), F.desc("purchases"), F.desc("views"))
        .limit(top_nodes)
        .withColumn("contract_version", F.lit(AFFINITY_CONTRACT_VERSION))
        .withColumnRenamed("product_id", "entity_id")
        .withColumn("entity_type", F.lit("product"))
        .withColumn("entity_label", F.concat(F.lit("product "), F.col("entity_id")))
        .withColumn("degree", F.lit(0).cast("long"))
        .withColumn("weighted_degree", F.lit(0.0))
        .withColumn("community_id", F.concat(F.lit("category:"), F.col("category_level1")))
        .select(
            "contract_version",
            "entity_id",
            "entity_type",
            "entity_label",
            "brand",
            "category_level1",
            "views",
            "carts",
            "purchases",
            "revenue",
            "degree",
            "weighted_degree",
            "community_id",
        )
    )


def build_relation_edges(
    product_sessions: DataFrame,
    pair_base: DataFrame,
    relation_type: str,
    event_flag: str,
    config: dict[str, Any],
) -> DataFrame:
    source_counts = (
        product_sessions.filter(F.col(event_flag) == 1)
        .groupBy("product_id")
        .agg(F.countDistinct("user_session").alias("source_sessions"))
        .withColumnRenamed("product_id", "source_id")
    )
    target_counts = (
        product_sessions.filter(F.col(event_flag) == 1)
        .groupBy("product_id")
        .agg(F.countDistinct("user_session").alias("target_sessions"))
        .withColumnRenamed("product_id", "target_id")
    )
    total_sessions = max(product_sessions.select("user_session").distinct().count(), 1)
    source_col = f"source_{event_flag}"
    target_col = f"target_{event_flag}"
    return (
        pair_base.filter((F.col(source_col) == 1) & (F.col(target_col) == 1))
        .groupBy("source_id", "target_id", "source_brand", "target_brand", "source_category", "target_category")
        .agg(F.countDistinct("user_session").alias("support"), F.round(F.sum("pair_revenue"), 2).alias("revenue_overlap"))
        .join(source_counts, "source_id", "left")
        .join(target_counts, "target_id", "left")
        .filter(F.col("support") >= int(config["min_support"]))
        .withColumn("confidence", F.round(F.col("support") / F.when(F.col("source_sessions") == 0, None).otherwise(F.col("source_sessions")), 6))
        .withColumn(
            "lift",
            F.round(
                (F.col("support") * F.lit(float(total_sessions)))
                / F.when((F.col("source_sessions") * F.col("target_sessions")) == 0, None).otherwise(
                    F.col("source_sessions") * F.col("target_sessions")
                ),
                6,
            ),
        )
        .withColumn(
            "jaccard",
            F.round(
                F.col("support")
                / F.when((F.col("source_sessions") + F.col("target_sessions") - F.col("support")) == 0, None).otherwise(
                    F.col("source_sessions") + F.col("target_sessions") - F.col("support")
                ),
                6,
            ),
        )
        .withColumn("contract_version", F.lit(AFFINITY_CONTRACT_VERSION))
        .withColumn("source_type", F.lit("product"))
        .withColumn("target_type", F.lit("product"))
        .withColumn("source_label", F.concat(F.lit("product "), F.col("source_id")))
        .withColumn("target_label", F.concat(F.lit("product "), F.col("target_id")))
        .withColumn("relation_type", F.lit(relation_type))
        .withColumn("sample_sessions", F.col("support"))
        .withColumn(
            "quality_status",
            F.when(F.col("support") >= int(config["min_support"]) * 2, F.lit("passed")).otherwise(F.lit("needs_review")),
        )
        .select(
            "contract_version",
            "source_id",
            "target_id",
            "source_type",
            "target_type",
            "source_label",
            "target_label",
            "source_brand",
            "target_brand",
            "source_category",
            "target_category",
            "relation_type",
            "support",
            "confidence",
            "lift",
            "jaccard",
            "revenue_overlap",
            "sample_sessions",
            "quality_status",
        )
    )


def enrich_nodes_with_degrees(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    degree: dict[str, int] = {}
    weighted: dict[str, float] = {}
    for edge in edges:
        for key in (edge["source_id"], edge["target_id"]):
            degree[key] = degree.get(key, 0) + 1
            weighted[key] = weighted.get(key, 0.0) + float(edge.get("lift") or 0)
    for node in nodes:
        node["degree"] = degree.get(node["entity_id"], 0)
        node["weighted_degree"] = round(weighted.get(node["entity_id"], 0.0), 6)
    return sorted(nodes, key=lambda row: (-float(row["weighted_degree"]), -float(row["revenue"]), row["entity_id"]))


def build_opportunities(edges: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in edges:
        opportunity_type = _opportunity_type(edge)
        reason_codes = [edge["relation_type"]]
        if float(edge.get("lift") or 0) >= 2:
            reason_codes.append("high_lift")
        if edge["source_category"] == edge["target_category"]:
            reason_codes.append("same_category")
        else:
            reason_codes.append("cross_category")
        support = int(edge.get("support") or 0)
        confidence = float(edge.get("confidence") or 0)
        rows.append(
            {
                "contract_version": AFFINITY_CONTRACT_VERSION,
                "opportunity_id": f"{opportunity_type}:{edge['source_id']}:{edge['target_id']}:{edge['relation_type']}",
                "type": opportunity_type,
                "primary_entity": edge["source_id"],
                "primary_label": edge["source_label"],
                "related_entity": edge["target_id"],
                "related_label": edge["target_label"],
                "reason_codes": reason_codes,
                "estimated_revenue_pool": round(float(edge.get("revenue_overlap") or 0), 2),
                "confidence": round(confidence, 6),
                "lift": round(float(edge.get("lift") or 0), 6),
                "support": support,
                "risk_level": "low" if support >= 10 and confidence >= 0.1 else "medium",
                "action": _opportunity_action(opportunity_type),
            }
        )
    return sorted(rows, key=lambda row: (-row["lift"], -row["support"], row["opportunity_id"]))[:limit]


def build_communities(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_category: dict[str, dict[str, Any]] = {}
    edge_count: dict[str, int] = {}
    for edge in edges:
        if edge["source_category"] == edge["target_category"]:
            edge_count[edge["source_category"]] = edge_count.get(edge["source_category"], 0) + 1
    for node in nodes:
        category = node["category_level1"] or "unknown"
        row = by_category.setdefault(
            category,
            {
                "contract_version": AFFINITY_CONTRACT_VERSION,
                "community_id": f"category:{category}",
                "category_level1": category,
                "node_count": 0,
                "edge_count": 0,
                "revenue": 0.0,
                "top_entities": [],
                "recommended_action": "Use community neighbors for category-level cross-sell review.",
            },
        )
        row["node_count"] += 1
        row["revenue"] = round(float(row["revenue"]) + float(node.get("revenue") or 0), 2)
        if len(row["top_entities"]) < 5:
            row["top_entities"].append(node["entity_id"])
    for category, row in by_category.items():
        row["edge_count"] = edge_count.get(category, 0)
    return sorted(by_category.values(), key=lambda row: (-row["edge_count"], -row["revenue"], row["community_id"]))


def build_centrality(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    communities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pagerank = _approximate_pagerank(nodes, edges)
    max_weighted_degree = max((float(node.get("weighted_degree") or 0) for node in nodes), default=0.0)
    community_lookup = {
        row["community_id"]: {
            "community_size": int(row.get("node_count") or 0),
            "community_revenue": float(row.get("revenue") or 0),
        }
        for row in communities
    }
    rows = []
    for node in nodes:
        normalized_weighted_degree = (
            round(float(node.get("weighted_degree") or 0) / max_weighted_degree, 6) if max_weighted_degree else 0.0
        )
        pagerank_score = pagerank.get(node["entity_id"], 0.0)
        centrality_score = round(normalized_weighted_degree * 0.55 + pagerank_score * 0.45, 6)
        community = community_lookup.get(node.get("community_id"), {"community_size": 0, "community_revenue": 0.0})
        rows.append(
            {
                "contract_version": AFFINITY_CONTRACT_VERSION,
                "entity_id": node["entity_id"],
                "entity_label": node["entity_label"],
                "brand": node.get("brand") or "unknown",
                "category_level1": node.get("category_level1") or "unknown",
                "community_id": node.get("community_id") or "unknown",
                "degree": int(node.get("degree") or 0),
                "weighted_degree": round(float(node.get("weighted_degree") or 0), 6),
                "normalized_weighted_degree": normalized_weighted_degree,
                "pagerank_score": pagerank_score,
                "centrality_score": centrality_score,
                "community_size": int(community["community_size"]),
                "community_revenue": round(float(community["community_revenue"]), 2),
                "revenue": round(float(node.get("revenue") or 0), 2),
                "views": int(node.get("views") or 0),
                "purchases": int(node.get("purchases") or 0),
            }
        )
    return sorted(rows, key=lambda row: (-row["centrality_score"], -row["weighted_degree"], row["entity_id"]))


def _approximate_pagerank(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], iterations: int = 12) -> dict[str, float]:
    node_ids = {str(node["entity_id"]) for node in nodes}
    if not node_ids:
        return {}
    graph: dict[str, list[tuple[str, float]]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        source = str(edge.get("source_id"))
        target = str(edge.get("target_id"))
        if source not in node_ids or target not in node_ids:
            continue
        weight = max(float(edge.get("lift") or 0), 0.0) * max(float(edge.get("support") or 1), 1.0)
        weight = weight or 1.0
        graph[source].append((target, weight))
        graph[target].append((source, weight))
    node_count = len(node_ids)
    damping = 0.85
    ranks = {node_id: 1.0 / node_count for node_id in node_ids}
    for _ in range(iterations):
        next_ranks = {node_id: (1.0 - damping) / node_count for node_id in node_ids}
        dangling_rank = sum(ranks[node_id] for node_id, neighbors in graph.items() if not neighbors)
        if dangling_rank:
            for node_id in node_ids:
                next_ranks[node_id] += damping * dangling_rank / node_count
        for source, neighbors in graph.items():
            if not neighbors:
                continue
            total_weight = sum(weight for _, weight in neighbors) or 1.0
            for target, weight in neighbors:
                next_ranks[target] += damping * ranks[source] * weight / total_weight
        ranks = next_ranks
    max_rank = max(ranks.values(), default=0.0)
    return {node_id: round(rank / max_rank, 6) if max_rank else 0.0 for node_id, rank in ranks.items()}


def build_quality(
    product_sessions: DataFrame,
    eligible_sessions: DataFrame,
    pair_base: DataFrame,
    input_rows: int,
    edge_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    session_count = product_sessions.select("user_session").distinct().count()
    product_session_rows = product_sessions.count()
    eligible_session_count = eligible_sessions.count()
    pair_base_rows = pair_base.count()
    pair_rows_per_input_row = round(pair_base_rows / input_rows, 6) if input_rows else 0.0
    pair_rows_per_product_session = round(pair_base_rows / product_session_rows, 6) if product_session_rows else 0.0
    edge_count = len(edge_rows)
    sparse_graph = edge_count == 0 or eligible_session_count < int(config["min_eligible_sessions"])
    pair_explosion = pair_rows_per_input_row > float(config.get("max_pair_rows_per_input_row", 20))
    product_session_pair_explosion = pair_rows_per_product_session > float(config.get("max_pair_rows_per_product_session", 20))
    checks = [
        {
            "name": "eligible_session_count",
            "actual": int(eligible_session_count),
            "operator": ">=",
            "expected": int(config["min_eligible_sessions"]),
            "passed": eligible_session_count >= int(config["min_eligible_sessions"]),
        },
        {
            "name": "edge_count",
            "actual": edge_count,
            "operator": ">",
            "expected": 0,
            "passed": edge_count > 0,
        },
        {
            "name": "pair_rows_per_input_row",
            "actual": pair_rows_per_input_row,
            "operator": "<=",
            "expected": float(config.get("max_pair_rows_per_input_row", 20)),
            "passed": not pair_explosion,
        },
        {
            "name": "pair_rows_per_product_session",
            "actual": pair_rows_per_product_session,
            "operator": "<=",
            "expected": float(config.get("max_pair_rows_per_product_session", 20)),
            "passed": not product_session_pair_explosion,
        },
    ]
    warnings = []
    if sparse_graph:
        warnings.append("sparse_graph")
    if pair_explosion:
        warnings.append("pair_explosion")
    if product_session_pair_explosion:
        warnings.append("product_session_pair_explosion")
    return {
        "contract_version": AFFINITY_CONTRACT_VERSION,
        "quality_status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "passed": all(check["passed"] for check in checks),
        "input_rows": int(input_rows),
        "session_count": int(session_count),
        "product_session_rows": int(product_session_rows),
        "eligible_session_count": int(eligible_session_count),
        "pair_base_rows": int(pair_base_rows),
        "pair_rows_per_input_row": pair_rows_per_input_row,
        "pair_rows_per_product_session": pair_rows_per_product_session,
        "edge_count": edge_count,
        "min_support": int(config["min_support"]),
        "sparse_graph": sparse_graph,
        "warnings": warnings,
        "checks": checks,
    }


def build_summary(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    opportunities: list[dict[str, Any]],
    communities: list[dict[str, Any]],
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    strongest_edge = edges[0] if edges else None
    top_opportunity = opportunities[0] if opportunities else None
    return {
        "contract_version": AFFINITY_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "community_count": len(communities),
        "opportunity_count": len(opportunities),
        "eligible_session_count": quality["eligible_session_count"],
        "pair_base_rows": quality["pair_base_rows"],
        "pair_rows_per_input_row": quality["pair_rows_per_input_row"],
        "min_support": int(config["min_support"]),
        "quality_status": quality["quality_status"],
        "sparse_graph": quality["sparse_graph"],
        "strongest_edge": strongest_edge,
        "top_opportunity": top_opportunity,
        "recommended_action": "Use high-lift product relationships as cross-sell and bundle candidates; review support before rollout.",
    }


def _opportunity_type(edge: dict[str, Any]) -> str:
    if edge["relation_type"] == "co_purchase":
        return "bundle"
    if edge["source_category"] != edge["target_category"]:
        return "category_bridge"
    if edge["relation_type"] == "co_view" and edge["source_brand"] != edge["target_brand"]:
        return "substitute"
    return "cross_sell"


def _opportunity_action(opportunity_type: str) -> str:
    return {
        "bundle": "add_bundle_or_complete-the-look_slot",
        "category_bridge": "test_cross_category_recommendation",
        "substitute": "add_substitute_recommendation_guardrail",
        "cross_sell": "add_cross_sell_slot",
    }.get(opportunity_type, "review_affinity_evidence")


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}


def _create_frame(spark: SparkSession, rows: list[dict[str, Any]], schema: T.StructType) -> DataFrame:
    return spark.createDataFrame(rows, schema=schema)
