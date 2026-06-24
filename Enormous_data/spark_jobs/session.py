from __future__ import annotations

from typing import Any

from pyspark.sql import SparkSession


def build_spark(app_name: str, master: str | None = None, configs: dict[str, Any] | None = None) -> SparkSession:
    """Create one SparkSession for a job run."""
    import os
    import sys
    # 显式设置环境变量，强制 Worker 使用与 Driver 相同的 Python 解释器，以防版本不一致导致 PYTHON_VERSION_MISMATCH 报错
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    builder = SparkSession.builder.appName(app_name)
    if master:
        builder = builder.master(master)

    for key, value in (configs or {}).items():
        if value is not None:
            builder = builder.config(key, str(value))

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
