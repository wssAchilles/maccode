from __future__ import annotations

from pyspark.sql import Column, DataFrame
from pyspark.sql.types import IntegerType, StructField, StructType


def with_global_rank(
    frame: DataFrame,
    order_by: list[Column],
    *,
    rank_col: str = "rank",
    limit: int | None = None,
) -> DataFrame:
    """Add a deterministic global rank without Spark's unpartitioned WindowExec path."""
    ordered = frame.orderBy(*order_by)
    if limit is not None:
        ordered = ordered.limit(int(limit))

    schema = StructType([StructField(rank_col, IntegerType(), False), *ordered.schema.fields])
    ranked_rows = ordered.rdd.zipWithIndex().map(lambda item: (int(item[1]) + 1, *tuple(item[0])))
    return frame.sparkSession.createDataFrame(ranked_rows, schema)
