from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession

from spark_jobs.schemas import ECOMMERCE_EVENT_SCHEMA


def read_events(
    spark: SparkSession,
    input_path: str,
    input_format: str = "csv",
    delimiter: str = ",",
) -> DataFrame:
    """Read ecommerce events from local or HDFS paths."""
    fmt = input_format.lower()

    if fmt == "csv":
        return (
            spark.read.option("header", True)
            .option("delimiter", delimiter)
            .schema(ECOMMERCE_EVENT_SCHEMA)
            .csv(input_path)
        )

    if fmt == "json":
        return spark.read.schema(ECOMMERCE_EVENT_SCHEMA).json(input_path)

    if fmt == "parquet":
        return spark.read.parquet(input_path)

    if fmt == "txt":
        return (
            spark.read.option("header", True)
            .option("delimiter", delimiter)
            .schema(ECOMMERCE_EVENT_SCHEMA)
            .csv(input_path)
        )

    raise ValueError(f"Unsupported input format: {input_format}")
