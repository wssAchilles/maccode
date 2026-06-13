from __future__ import annotations

from functools import reduce
from itertools import combinations
from typing import Any, Iterable

from pyspark import StorageLevel
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_jobs.dashboard_semantics import (
    DASHBOARD_CUBE_ALL_VALUE,
    DASHBOARD_CUBE_CONTRACT_VERSION,
    DASHBOARD_SEMANTIC_VERSION,
    dashboard_metric_definitions,
)


DASHBOARD_CUBE_DIMENSIONS = ("event_type", "category_level1", "brand")


def build_dashboard_cube_outputs(
    cleaned_df: DataFrame,
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    prepared = _prepare_events(cleaned_df)
    total_cube = build_dashboard_cube(prepared, include_date=False).persist(StorageLevel.MEMORY_AND_DISK)
    daily_cube = build_dashboard_cube(prepared, include_date=True).persist(StorageLevel.MEMORY_AND_DISK)
    total_rows = total_cube.count()
    daily_rows = daily_cube.count()
    metric_definitions = dashboard_metric_definitions(run_id)
    summary = {
        "contract_version": DASHBOARD_CUBE_CONTRACT_VERSION,
        "semantic_version": DASHBOARD_SEMANTIC_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "metric_grain": "筛选维度汇总 / 日级趋势",
        "dimensions": list(DASHBOARD_CUBE_DIMENSIONS),
        "summary_cube_rows": int(total_rows),
        "daily_cube_rows": int(daily_rows),
        "cube_row_count": int(total_rows + daily_rows),
        "metric_count": len(metric_definitions),
    }
    return (
        {
            "dashboard_cube_total": total_cube,
            "dashboard_cube_daily": daily_cube,
        },
        {
            "dashboard_cube_summary": summary,
            "dashboard_semantic_metrics": metric_definitions,
        },
    )


def build_dashboard_cube(prepared_df: DataFrame, *, include_date: bool) -> DataFrame:
    cubes = [
        _aggregate_dimension_subset(prepared_df, dimensions, include_date=include_date)
        for dimensions in _dimension_subsets(DASHBOARD_CUBE_DIMENSIONS)
    ]
    return reduce(lambda left, right: left.unionByName(right), cubes)


def _prepare_events(cleaned_df: DataFrame) -> DataFrame:
    return (
        cleaned_df.withColumn("dt", F.coalesce(F.col("event_date").cast("string"), F.lit("unknown")))
        .withColumn("event_type", F.coalesce(F.nullif(F.trim(F.col("event_type")), F.lit("")), F.lit("unknown")))
        .withColumn("category_level1", F.coalesce(F.nullif(F.trim(F.col("category_level1")), F.lit("")), F.lit("unknown")))
        .withColumn("brand", F.coalesce(F.nullif(F.trim(F.col("brand")), F.lit("")), F.lit("unknown")))
        .withColumn("purchase_flag", F.when(F.col("event_type") == "purchase", F.lit(1)).otherwise(F.lit(0)))
        .withColumn(
            "purchase_value",
            F.when(F.col("event_type") == "purchase", F.coalesce(F.col("price"), F.lit(0.0))).otherwise(F.lit(0.0)),
        )
    )


def _aggregate_dimension_subset(prepared_df: DataFrame, dimensions: tuple[str, ...], *, include_date: bool) -> DataFrame:
    group_columns = ["dt"] if include_date else []
    group_columns.extend(dimensions)
    aggregated = prepared_df.groupBy(*group_columns).agg(
        F.count("*").cast("long").alias("event_count"),
        F.sum("purchase_flag").cast("long").alias("purchase_count"),
        F.round(F.sum("purchase_value"), 2).alias("total_sales"),
        F.countDistinct("user_id").cast("long").alias("unique_users"),
        F.countDistinct("user_session").cast("long").alias("unique_sessions"),
    )
    selected = [
        F.col("dt") if include_date else F.lit(DASHBOARD_CUBE_ALL_VALUE).alias("dt"),
        *[
            F.col(dimension) if dimension in dimensions else F.lit(DASHBOARD_CUBE_ALL_VALUE).alias(dimension)
            for dimension in DASHBOARD_CUBE_DIMENSIONS
        ],
        F.col("event_count"),
        F.col("purchase_count"),
        F.col("total_sales"),
        F.col("unique_users"),
        F.col("unique_sessions"),
    ]
    return (
        aggregated.select(*selected)
        .withColumn(
            "avg_order_value",
            F.when(F.col("purchase_count") > 0, F.round(F.col("total_sales") / F.col("purchase_count"), 2)).otherwise(F.lit(0.0)),
        )
        .withColumn("grain", F.lit("daily" if include_date else "total"))
        .withColumn("contract_version", F.lit(DASHBOARD_CUBE_CONTRACT_VERSION))
    )


def _dimension_subsets(dimensions: Iterable[str]) -> list[tuple[str, ...]]:
    items = tuple(dimensions)
    return [tuple(combo) for size in range(len(items) + 1) for combo in combinations(items, size)]
