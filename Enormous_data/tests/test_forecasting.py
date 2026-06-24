from __future__ import annotations

import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from spark_jobs.forecasting import FORECAST_CONTRACT_VERSION, build_forecasting_outputs, forecasting_config


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[2]")
        .appName("forecasting-test")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_forecasting_outputs_sparse_fallback_and_quality_gate(spark):
    rows = [
        {"event_time": "2019-11-01 00:00:00", "event_type": "view", "product_id": 1, "category_level1": "electronics", "price": 999.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:01:00", "event_type": "purchase", "product_id": 1, "category_level1": "electronics", "price": 100.0, "user_id": 10, "user_session": "s1"},
        {"event_time": "2019-11-01 00:02:00", "event_type": "purchase", "product_id": 2, "category_level1": "apparel", "price": 50.0, "user_id": 11, "user_session": "s2"},
    ]
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 3, "min_history_days": 7, "top_entities": 2}),
        run_id="forecast-test",
        input_snapshot={"actual_input_path": "hdfs://master:9000/user/course/ecommerce_behavior/*.csv", "storage_mode": "hdfs"},
    )

    summary = metrics["forecasting_summary"]
    assert summary["contract_version"] == FORECAST_CONTRACT_VERSION
    assert summary["site_forecast_gmv"] == 450.0
    assert summary["site_forecast_purchase_count"] == 6.0
    assert summary["quality_status"] == "needs_review"
    assert summary["history_days"] == 1
    assert metrics["forecasting_quality"]["passed"] is False
    assert any(row["fallback_reason"] == "insufficient_history_days" for row in metrics["forecasting_entities"])
    assert any(row["metric"] == "gmv" for row in metrics["forecasting_series"])


def test_forecasting_backtest_generates_error_rows_when_history_exists(spark):
    rows = []
    for day, price in [("2019-11-01", 100.0), ("2019-11-02", 120.0), ("2019-11-03", 80.0)]:
        rows.append(
            {
                "event_time": f"{day} 00:00:00",
                "event_type": "purchase",
                "product_id": 1,
                "category_level1": "electronics",
                "price": price,
                "user_id": 10,
                "user_session": f"s-{day}",
            }
        )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 2, "backtest_window_days": 1, "min_history_days": 2}),
        run_id="forecast-backtest",
        input_snapshot={},
    )

    assert metrics["forecasting_backtest"]
    assert metrics["forecasting_evaluation"]["model_metrics"]
    assert any(row["group"].startswith("h") for row in metrics["forecasting_evaluation"]["horizon_metrics"])
    assert metrics["forecasting_quality"]["metrics"]["site_wape"] is not None
    assert metrics["forecasting_summary"]["history_days"] == 3


def test_forecasting_excludes_incomplete_trailing_day_from_quality(spark):
    rows = []
    for index in range(10):
        day = f"2019-11-{index + 1:02d}"
        price = 10.0 if index == 9 else 100.0
        rows.append(
            {
                "event_time": f"{day} 00:00:00",
                "event_type": "purchase",
                "product_id": 1,
                "category_level1": "electronics",
                "price": price,
                "user_id": index,
                "user_session": f"s-{day}",
            }
        )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"backtest_window_days": 2, "min_history_days": 2}),
        run_id="forecast-incomplete-tail",
        input_snapshot={},
    )

    quality = metrics["forecasting_quality"]
    assert quality["metrics"]["excluded_incomplete_dates"] == ["2019-11-10"]
    assert metrics["forecasting_summary"]["history_range"]["max_dt"] == "2019-11-09"


def test_forecasting_collects_only_site_and_top_entities_for_driver_outputs(spark):
    rows = []
    for category_index in range(5):
        for day_index in range(2):
            rows.append(
                {
                    "event_time": f"2019-11-{day_index + 1:02d} 00:00:00",
                    "event_type": "purchase",
                    "product_id": category_index,
                    "category_level1": f"cat-{category_index}",
                    "price": 100.0 + category_index,
                    "user_id": category_index * 10 + day_index,
                    "user_session": f"s-{category_index}-{day_index}",
                }
            )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    frames, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"top_entities": 2, "forecast_horizon_days": 1, "preview_limit": 20, "min_history_days": 1}),
        run_id="forecast-top-entities",
        input_snapshot={},
    )

    assert frames["daily_demand"].filter(F.col("scope") == "category").select("entity_key").distinct().count() == 5
    assert metrics["forecasting_summary"]["entity_count"] == 3
    assert {row["scope"] for row in metrics["forecasting_entities"]} == {"site", "category"}


def test_forecasting_caps_driver_history_rows(spark):
    rows = []
    for category_index in range(5):
        for day_index in range(4):
            rows.append(
                {
                    "event_time": f"2019-11-{day_index + 1:02d} 00:00:00",
                    "event_type": "purchase",
                    "product_id": category_index,
                    "category_level1": f"cat-{category_index}",
                    "price": 100.0 + category_index,
                    "user_id": category_index * 10 + day_index,
                    "user_session": f"s-{category_index}-{day_index}",
                }
            )
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))

    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config(
            {
                "top_entities": 3,
                "forecast_horizon_days": 1,
                "history_collect_days": 10,
                "max_driver_history_rows": 8,
                "min_history_days": 1,
            }
        ),
        run_id="forecast-driver-cap",
        input_snapshot={},
    )

    quality_metrics = metrics["forecasting_quality"]["metrics"]
    assert quality_metrics["driver_history_rows"] <= 8
    assert quality_metrics["collected_history_days"] == 2
    assert metrics["forecasting_summary"]["max_driver_history_rows"] == 8
    assert any(check["name"] == "driver_history_rows" and check["passed"] for check in metrics["forecasting_quality"]["checks"])


def test_forecasting_hts_reconciliation(spark):
    rows = []
    # 构造 9 天的历史数据，有 3 个 Category
    for day in range(1, 10):
        dt = f"2019-11-{day:02d}"
        rows.append({"event_time": f"{dt} 10:00:00", "event_type": "purchase", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": 1, "user_session": f"s1-{day}"})
        rows.append({"event_time": f"{dt} 11:00:00", "event_type": "purchase", "product_id": 102, "category_level1": "cat-2", "price": 200.0, "user_id": 2, "user_session": f"s2-{day}"})
        rows.append({"event_time": f"{dt} 12:00:00", "event_type": "purchase", "product_id": 103, "category_level1": "cat-3", "price": 300.0, "user_id": 3, "user_session": f"s3-{day}"})
        rows.append({"event_time": f"{dt} 09:00:00", "event_type": "view", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": 1, "user_session": f"s1-{day}"})
        rows.append({"event_time": f"{dt} 09:30:00", "event_type": "view", "product_id": 102, "category_level1": "cat-2", "price": 200.0, "user_id": 2, "user_session": f"s2-{day}"})

    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))
    
    # 预测未来 3 天
    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 3, "min_history_days": 5, "top_entities": 3}),
        run_id="forecast-hts-test",
        input_snapshot={},
    )
    
    series = metrics["forecasting_series"]
    by_dt_metric = {}
    for r in series:
        key = (r["dt"], r["metric"])
        by_dt_metric.setdefault(key, []).append(r)
        
    assert by_dt_metric
    for (dt, metric), group in by_dt_metric.items():
        site_val = sum(float(r["forecast_value"]) for r in group if r["scope"] == "site")
        cats_val = sum(float(r["forecast_value"]) for r in group if r["scope"] == "category")
        assert abs(site_val - cats_val) <= 0.05


def test_forecasting_views_covariate(spark):
    rows = []
    # 历史正常销量 100 与流量 10
    for day in range(1, 8):
        dt = f"2019-11-{day:02d}"
        rows.append({"event_time": f"{dt} 10:00:00", "event_type": "purchase", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": 1, "user_session": f"s-{day}"})
        for v in range(10):
            rows.append({"event_time": f"{dt} 09:00:00", "event_type": "view", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": v, "user_session": f"s-{day}"})
            
    # 回测日期（第8天）流量暴增为 20（均值的2倍）
    dt_ho = "2019-11-08"
    rows.append({"event_time": f"{dt_ho} 10:00:00", "event_type": "purchase", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": 1, "user_session": "s-ho"})
    for v in range(20):
        rows.append({"event_time": f"{dt_ho} 09:00:00", "event_type": "view", "product_id": 101, "category_level1": "cat-1", "price": 100.0, "user_id": v, "user_session": "s-ho"})
        
    df = spark.createDataFrame(rows).withColumn("event_timestamp", F.to_timestamp("event_time"))
    
    _, metrics = build_forecasting_outputs(
        df,
        forecasting_config({"forecast_horizon_days": 1, "backtest_window_days": 1, "min_history_days": 5, "top_entities": 1}),
        run_id="forecast-covariate-test",
        input_snapshot={},
    )
    
    backtest = metrics["forecasting_backtest"]
    cat_bt = [r for r in backtest if r["entity_key"] == "cat-1" and r["dt"] == "2019-11-08"][0]
    
    # 因为流量增加了一倍，协变量乘数为 2.0，预测应显着增加
    assert cat_bt["forecast"] > 110.0


def test_forecasting_global_neural_network_convergence():
    from spark_jobs.forecasting import GlobalARMLP
    import numpy as np

    # 构造确定性的模拟回归数据集 (16维输入，2维输出)
    np.random.seed(42)
    n_samples = 100
    X = np.random.randn(n_samples, 16).astype(np.float32)
    w_true = np.random.randn(16, 2).astype(np.float32)
    Y = np.dot(np.maximum(0, X), w_true) + np.random.randn(n_samples, 2).astype(np.float32) * 0.1

    # 缩放系数
    scale_x = np.max(np.abs(X), axis=0)
    scale_x[scale_x == 0] = 1.0
    scale_y = np.max(np.abs(Y), axis=0)
    scale_y[scale_y == 0] = 1.0

    X_scaled = X / scale_x
    Y_scaled = Y / scale_y

    model = GlobalARMLP(input_dim=16, hidden_dim=32, output_dim=2)

    # 计算初始损失
    y_hat_scaled, _, _ = model.forward(X_scaled)
    init_loss = np.mean((y_hat_scaled - Y_scaled) ** 2)

    # 训练 100 次迭代
    losses = []
    for epoch in range(100):
        loss = model.train_step(X_scaled, Y_scaled, lr=0.1)
        losses.append(loss)

    # 验证最终损失已显著单调下降
    assert losses[-1] < init_loss * 0.2
    assert losses[-1] < 0.15


def test_forecasting_coldstart_prior_inheritance():
    from spark_jobs.forecasting import build_forecast_rows
    
    # 构造测试数据
    rows = []
    # 1. 构造一个已有的 category，提供常态数据，平均 GMV 为 1000.0， purchases 为 10.0
    for day in range(1, 10):
        dt = f"2019-11-{day:02d}"
        rows.append({
            "dt": dt,
            "scope": "category",
            "entity_key": "old_category",
            "entity_label": "old_category",
            "gmv": 1000.0,
            "purchase_count": 10.0,
            "views": 100.0
        })
    # 2. 构造一个完全冷启动的新 category
    rows.append({
        "dt": "2019-11-09",
        "scope": "category",
        "entity_key": "new_category",
        "entity_label": "new_category",
        "gmv": 0.0,
        "purchase_count": 0.0,
        "views": 1.0
    })
    
    config = {
        "forecast_horizon_days": 1,
        "min_history_days": 5,
        "top_entities": 10,
        "training_window_days": 7
    }
    
    results = build_forecast_rows(rows, config)
    
    # 验证新 category 在预测中继承了先验期望，因此其 gmv 和 purchase_count 预测值均显著大于 0
    new_cat_rows = [r for r in results if r["entity_key"] == "new_category"]
    assert len(new_cat_rows) >= 2
    
    gmv_row = [r for r in new_cat_rows if r["metric"] == "gmv"][0]
    purchases_row = [r for r in new_cat_rows if r["metric"] == "purchase_count"][0]
    
    # 品类均值 gmv=1000, purchases=10.0；冷启动继承 70% 权重 => gmv 应接近 700.0, purchases 接近 7.0
    assert gmv_row["forecast_value"] > 100.0
    assert purchases_row["forecast_value"] > 1.0
