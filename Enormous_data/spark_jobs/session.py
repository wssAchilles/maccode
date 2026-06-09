from __future__ import annotations

from typing import Any

from pyspark.sql import SparkSession


def build_spark(app_name: str, master: str | None = None, configs: dict[str, Any] | None = None) -> SparkSession:
    """Create one SparkSession for a job run."""
    builder = SparkSession.builder.appName(app_name)
    if master:
        builder = builder.master(master)

    for key, value in (configs or {}).items():
        if value is not None:
            builder = builder.config(key, str(value))

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
