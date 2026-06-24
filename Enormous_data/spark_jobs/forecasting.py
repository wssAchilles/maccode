from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark import StorageLevel


class GlobalARMLP:
    """纯 NumPy 手写的全局自回归多层感知机时序预测模型 (Global AR-MLP)"""
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 2):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # He 初始化防止 ReLU 死亡
        self.w1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, hidden_dim))
        self.w2 = np.random.randn(hidden_dim, output_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros((1, output_dim))
        
        # 动量缓冲区
        self.v_w1 = np.zeros_like(self.w1)
        self.v_b1 = np.zeros_like(self.b1)
        self.v_w2 = np.zeros_like(self.w2)
        self.v_b2 = np.zeros_like(self.b2)

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        # x 形状为 (N, input_dim)
        z1 = np.dot(x, self.w1) + self.b1
        a1 = np.maximum(0, z1)  # ReLU
        y_hat = np.dot(a1, self.w2) + self.b2  # 线性输出
        return y_hat, z1, a1

    def train_step(self, x: np.ndarray, y: np.ndarray, lr: float = 0.01, beta: float = 0.9) -> float:
        n = x.shape[0]
        y_hat, z1, a1 = self.forward(x)
        loss = np.mean((y_hat - y) ** 2)
        
        # 反向传播计算梯度
        dy_hat = 2.0 * (y_hat - y) / n
        dw2 = np.dot(a1.T, dy_hat)
        db2 = np.sum(dy_hat, axis=0, keepdims=True)
        
        da1 = np.dot(dy_hat, self.w2.T)
        dz1 = da1 * (z1 > 0)
        dw1 = np.dot(x.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)
        
        # 动量更新参数
        self.v_w1 = beta * self.v_w1 + (1.0 - beta) * dw1
        self.w1 -= lr * self.v_w1
        
        self.v_b1 = beta * self.v_b1 + (1.0 - beta) * db1
        self.b1 -= lr * self.v_b1
        
        self.v_w2 = beta * self.v_w2 + (1.0 - beta) * dw2
        self.w2 -= lr * self.v_w2
        
        self.v_b2 = beta * self.v_b2 + (1.0 - beta) * db2
        self.b2 -= lr * self.v_b2
        
        return float(loss)


def _prepare_training_data(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    entities = select_entities(daily_rows, int(config["top_entities"]))
    X_list = []
    Y_list = []
    for (scope, entity_key), rows in entities.items():
        ordered = sorted(rows, key=lambda row: row["dt"])
        if len(ordered) < 8:
            continue
        
        views_history = [float(r.get("views") or 0.0) for r in ordered]
        avg_views = _mean(views_history) if views_history else 1.0
        if avg_views <= 0:
            avg_views = 1.0

        for k in range(7, len(ordered)):
            target_row = ordered[k]
            lag1_gmv = float(ordered[k-1].get("gmv") or 0.0)
            lag2_gmv = float(ordered[k-2].get("gmv") or 0.0)
            lag3_gmv = float(ordered[k-3].get("gmv") or 0.0)
            lag7_gmv = float(ordered[k-7].get("gmv") or 0.0)

            lag1_p = float(ordered[k-1].get("purchase_count") or 0.0)
            lag2_p = float(ordered[k-2].get("purchase_count") or 0.0)
            lag3_p = float(ordered[k-3].get("purchase_count") or 0.0)
            lag7_p = float(ordered[k-7].get("purchase_count") or 0.0)

            weekday_val = _parse_date(target_row["dt"]).weekday()
            weekday_onehot = [0.0] * 7
            weekday_onehot[weekday_val] = 1.0

            actual_views = float(target_row.get("views") or 0.0)
            views_factor = min(max(actual_views / avg_views, 0.5), 2.0)

            features = [
                lag1_gmv, lag2_gmv, lag3_gmv, lag7_gmv,
                lag1_p, lag2_p, lag3_p, lag7_p,
                *weekday_onehot,
                views_factor
            ]
            X_list.append(features)
            Y_list.append([float(target_row.get("gmv") or 0.0), float(target_row.get("purchase_count") or 0.0)])
            
    if not X_list:
        return np.empty((0, 16), dtype=np.float32), np.empty((0, 2), dtype=np.float32), np.ones(16, dtype=np.float32), np.ones(2, dtype=np.float32)
        
    X = np.array(X_list, dtype=np.float32)
    Y = np.array(Y_list, dtype=np.float32)
    
    scale_X = np.max(np.abs(X), axis=0)
    scale_X[scale_X == 0] = 1.0
    scale_Y = np.max(np.abs(Y), axis=0)
    scale_Y[scale_Y == 0] = 1.0
    
    return X, Y, scale_X, scale_Y


def _train_global_model(X: np.ndarray, Y: np.ndarray, scale_X: np.ndarray, scale_Y: np.ndarray) -> GlobalARMLP:
    model = GlobalARMLP(input_dim=16, hidden_dim=64, output_dim=2)
    X_scaled = X / scale_X
    Y_scaled = Y / scale_Y
    
    epochs = 150
    lr = 0.05
    for epoch in range(epochs):
        current_lr = lr * (0.95 ** (epoch // 20))
        model.train_step(X_scaled, Y_scaled, lr=current_lr)
    return model


FORECAST_CONTRACT_VERSION = "demand-forecasting/v1"

DEFAULT_CONFIG: dict[str, Any] = {
    "forecast_horizon_days": 7,
    "training_window_days": 28,
    "backtest_window_days": 7,
    "backtest_windows": [1, 3, 7],
    "preview_limit": 100,
    "top_entities": 12,
    "min_history_days": 7,
    "max_site_wape": 0.35,
    "min_trailing_day_actual_ratio": 0.5,
    "high_risk_drop_rate": -0.15,
    "medium_risk_drop_rate": -0.08,
    "history_collect_days": 90,
    "max_driver_history_rows": 2000,
}


def forecasting_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_CONFIG, **(config or {})}


def build_forecasting_outputs(
    cleaned_df: DataFrame,
    config: dict[str, Any],
    *,
    run_id: str,
    input_snapshot: dict[str, Any],
) -> tuple[dict[str, DataFrame], dict[str, Any]]:
    daily = build_daily_demand(cleaned_df).persist(StorageLevel.MEMORY_AND_DISK)
    history_days = _bounded_history_days(config)
    max_driver_history_rows = int(config["max_driver_history_rows"])
    selected_daily = select_forecast_daily_rows(
        daily,
        int(config["top_entities"]),
        history_days,
    ).limit(max_driver_history_rows)
    daily_rows = [
        _json_safe(row.asDict())
        for row in selected_daily.collect()
    ]
    driver_history = {
        "requested_history_days": int(config["history_collect_days"]),
        "collected_history_days": history_days,
        "max_driver_history_rows": max_driver_history_rows,
        "driver_history_rows": len(daily_rows),
    }
    complete_daily_rows, excluded_dates = exclude_incomplete_trailing_dates(daily_rows, config)
    raw_forecast_rows = build_forecast_rows(complete_daily_rows, config)
    # 层次时序预测对齐
    forecast_rows = reconcile_hierarchical_forecasts(raw_forecast_rows, complete_daily_rows)
    entity_rows = build_entity_rows(complete_daily_rows, forecast_rows, config)
    backtest_rows = build_backtest_rows(complete_daily_rows, config)
    evaluation = build_backtest_evaluation(backtest_rows, config, run_id)
    quality = build_quality(complete_daily_rows, backtest_rows, config, excluded_dates, driver_history)
    risks = build_risks(entity_rows, config)
    summary = build_summary(complete_daily_rows, forecast_rows, entity_rows, risks, quality, config, run_id, input_snapshot, driver_history)

    spark = cleaned_df.sparkSession
    forecast_frame = spark.createDataFrame(forecast_rows) if forecast_rows else spark.createDataFrame([], daily.schema)
    entity_frame = spark.createDataFrame(entity_rows) if entity_rows else spark.createDataFrame([], daily.schema)
    frames = {
        "daily_demand": daily,
        "forecast_series": forecast_frame,
        "forecast_entities": entity_frame,
    }
    metrics = {
        "forecasting_summary": summary,
        # 保留完整预测时间线，确保前端可选实体折线图均有数据
        "forecasting_series": forecast_rows,
        "forecasting_entities": entity_rows[: int(config["preview_limit"])],
        # 保留完整回测结果，防止因截断导致回测曲线缺失
        "forecasting_backtest": backtest_rows,
        "forecasting_evaluation": evaluation,
        "forecasting_risks": risks[: int(config["preview_limit"])],
        "forecasting_quality": quality,
    }
    return frames, metrics


def build_daily_demand(cleaned_df: DataFrame) -> DataFrame:
    purchase = F.col("event_type") == "purchase"
    base = cleaned_df.withColumn("dt", F.to_date("event_timestamp"))
    site = (
        base.groupBy("dt")
        .agg(
            F.countDistinct("user_session").alias("session_count"),
            F.countDistinct(F.when(purchase, F.col("user_id"))).alias("buyer_count"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("site"))
        .withColumn("entity_key", F.lit("all"))
        .withColumn("entity_label", F.lit("全站"))
    )
    category = (
        base.groupBy("dt", "category_level1")
        .agg(
            F.countDistinct("user_session").alias("session_count"),
            F.countDistinct(F.when(purchase, F.col("user_id"))).alias("buyer_count"),
            F.count(F.when(purchase, F.lit(1))).alias("purchase_count"),
            F.round(F.sum(F.when(purchase, F.coalesce(F.col("price"), F.lit(0))).otherwise(F.lit(0))), 2).alias("gmv"),
            F.count(F.when(F.col("event_type") == "view", F.lit(1))).alias("views"),
        )
        .withColumn("scope", F.lit("category"))
        .withColumnRenamed("category_level1", "entity_key")
        .withColumn("entity_label", F.col("entity_key"))
    )
    return (
        site.unionByName(category)
        .withColumn("avg_order_value", F.round(F.col("gmv") / F.when(F.col("purchase_count") == 0, None).otherwise(F.col("purchase_count")), 2))
        .withColumn("view_to_purchase_rate", F.round(F.col("purchase_count") / F.when(F.col("views") == 0, None).otherwise(F.col("views")), 6))
        .withColumn("dt", F.date_format("dt", "yyyy-MM-dd"))
        .select(
            "dt",
            "scope",
            "entity_key",
            "entity_label",
            "session_count",
            "buyer_count",
            "purchase_count",
            "gmv",
            "views",
            "avg_order_value",
            "view_to_purchase_rate",
        )
    )


def select_forecast_daily_rows(daily: DataFrame, top_entities: int, history_days: int | None = None) -> DataFrame:
    bounded_daily = daily
    if history_days and history_days > 0:
        latest = daily.agg(F.max(F.to_date("dt")).alias("latest_dt"))
        bounded_daily = (
            daily.crossJoin(latest)
            .where(F.col("latest_dt").isNull() | (F.to_date("dt") >= F.date_sub(F.col("latest_dt"), history_days - 1)))
            .drop("latest_dt")
        )
    site_rows = bounded_daily.filter(F.col("scope") == "site")
    top_categories = (
        bounded_daily.filter(F.col("scope") == "category")
        .groupBy("entity_key")
        .agg(F.sum("gmv").alias("entity_gmv"))
        .orderBy(F.desc("entity_gmv"), "entity_key")
        .limit(top_entities)
        .select("entity_key")
    )
    category_rows = bounded_daily.filter(F.col("scope") == "category").join(top_categories, "entity_key", "inner")
    return site_rows.unionByName(category_rows).orderBy("scope", "entity_key", "dt")


def _bounded_history_days(config: dict[str, Any]) -> int:
    requested_days = max(1, int(config["history_collect_days"]))
    entity_slots = max(1, int(config["top_entities"]) + 1)
    max_rows = max(1, int(config["max_driver_history_rows"]))
    max_days_by_rows = max(1, max_rows // entity_slots)
    return min(requested_days, max_days_by_rows)


def exclude_incomplete_trailing_dates(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    site_rows = sorted([row for row in daily_rows if row["scope"] == "site"], key=lambda row: row["dt"])
    if len(site_rows) < 3:
        return daily_rows, []

    latest = site_rows[-1]
    comparison_window = site_rows[-min(8, len(site_rows)) : -1]
    baseline = _median([float(row.get("gmv") or 0) for row in comparison_window])
    latest_gmv = float(latest.get("gmv") or 0)
    threshold = float(config["min_trailing_day_actual_ratio"])
    if baseline <= 0 or latest_gmv >= baseline * threshold:
        return daily_rows, []

    excluded = latest["dt"]
    return [row for row in daily_rows if row["dt"] != excluded], [excluded]


def build_forecast_rows(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(config["forecast_horizon_days"])
    entities = select_entities(daily_rows, int(config["top_entities"]))
    
    # 预先计算各品类的先验销量与期望营收均值，用于冷启动新品的基线平滑继承
    category_priors_gmv: dict[str, float] = {}
    category_priors_purchases: dict[str, float] = {}
    for (s, ek), ent_rows in entities.items():
        if s == "category":
            gmv_vals = [float(r.get("gmv") or 0.0) for r in ent_rows if float(r.get("gmv") or 0.0) > 0]
            pur_vals = [float(r.get("purchase_count") or 0.0) for r in ent_rows if float(r.get("purchase_count") or 0.0) > 0]
            if gmv_vals:
                category_priors_gmv[ek] = sum(gmv_vals) / len(gmv_vals)
            if pur_vals:
                category_priors_purchases[ek] = sum(pur_vals) / len(pur_vals)

    # 1. 准备训练数据并训练手写全局自回归神经网络
    X, Y, scale_X, scale_Y = _prepare_training_data(daily_rows, config)
    if X.shape[0] > 10:
        global_model = _train_global_model(X, Y, scale_X, scale_Y)
        has_nn = True
    else:
        global_model = None
        has_nn = False

    results: list[dict[str, Any]] = []
    
    for (scope, entity_key), rows in entities.items():
        ordered = sorted(rows, key=lambda row: row["dt"])
        max_dt = _parse_date(ordered[-1]["dt"])
        history_days = len({row["dt"] for row in ordered})
        sparse = history_days < int(config["min_history_days"])
        interval_width = 0.65 if sparse else 0.22
        
        recent = ordered[-min(len(ordered), int(config["training_window_days"])) :]
        baseline_gmv = _mean([float(row.get("gmv") or 0) for row in recent])
        baseline_purchases = _mean([float(row.get("purchase_count") or 0) for row in recent])
        
        # 提取当前实体所属品类，执行冷启动新品先验期望继承
        label_parts = [p.strip() for p in ordered[-1]["entity_label"].split("/")]
        cat_key = label_parts[-1] if label_parts else ""
        prior_gmv = category_priors_gmv.get(cat_key, 500.0)
        prior_purchases = category_priors_purchases.get(cat_key, 5.0)
        
        if sparse and scope != "site":
            # 冷启动新品销量/营收以 70% 权重融合所属品类的先验期望，修正零基线误报
            baseline_gmv = 0.3 * baseline_gmv + 0.7 * prior_gmv
            baseline_purchases = 0.3 * baseline_purchases + 0.7 * prior_purchases

        baseline_views = _mean([float(row.get("views") or 0) for row in recent])
        if baseline_views <= 0:
            baseline_views = 1.0

        # 如果神经网络就绪，我们进行自回归多步预测
        if has_nn and global_model is not None:
            # 建立滑动预测缓冲区，冷启动实体用均值补齐到 7 天
            recent_rows = ordered[-7:]
            while len(recent_rows) < 7:
                recent_rows.insert(0, {
                    "gmv": baseline_gmv,
                    "purchase_count": baseline_purchases,
                    "views": baseline_views,
                    "dt": ordered[0]["dt"]
                })
            
            # buffer 缓存最近 7 天的 (gmv, purchases) 用于自回归迭代
            buffer = [(float(r.get("gmv") or 0.0), float(r.get("purchase_count") or 0.0)) for r in recent_rows]

            for offset in range(1, horizon + 1):
                forecast_dt = max_dt + timedelta(days=offset)
                target_weekday = forecast_dt.weekday()
                weekday_onehot = [0.0] * 7
                weekday_onehot[target_weekday] = 1.0
                
                # views 因子
                same_weekday_views = [
                    float(row.get("views") or 0)
                    for row in ordered
                    if _parse_date(row["dt"]).weekday() == target_weekday
                ]
                expected_views = _mean(same_weekday_views[-4:]) if same_weekday_views else baseline_views
                views_factor = min(max(expected_views / baseline_views, 0.5), 2.0)
                
                # 构造输入特征 (16维)
                lag1 = buffer[-1]
                lag2 = buffer[-2]
                lag3 = buffer[-3]
                lag7 = buffer[-7]
                
                x_input = np.array([
                    lag1[0], lag2[0], lag3[0], lag7[0],
                    lag1[1], lag2[1], lag3[1], lag7[1],
                    *weekday_onehot,
                    views_factor
                ], dtype=np.float32)
                
                # 特征缩放后前传神经网络预测
                x_scaled = x_input / scale_X
                y_hat_scaled, _, _ = global_model.forward(x_scaled.reshape(1, -1))
                y_pred = y_hat_scaled[0] * scale_Y
                
                point_gmv = max(0.0, float(y_pred[0]))
                point_purchases = max(0.0, float(y_pred[1]))
                
                # 预测值滚入自回归 buffer
                buffer.append((point_gmv, point_purchases))
                
                results.append(
                    {
                        "contract_version": FORECAST_CONTRACT_VERSION,
                        "dt": forecast_dt.isoformat(),
                        "scope": scope,
                        "entity_key": entity_key,
                        "entity_label": ordered[-1]["entity_label"],
                        "metric": "gmv",
                        "forecast_value": round(point_gmv, 2),
                        "lower_bound": round(max(0.0, point_gmv * (1 - interval_width)), 2),
                        "upper_bound": round(point_gmv * (1 + interval_width), 2),
                        "history_days": history_days,
                        "model_name": "global_ar_mlp" if not sparse else "global_ar_mlp_coldstart",
                        "fallback_reason": "coldstart_history_sparse" if sparse else "",
                    }
                )
                results.append(
                    {
                        "contract_version": FORECAST_CONTRACT_VERSION,
                        "dt": forecast_dt.isoformat(),
                        "scope": scope,
                        "entity_key": entity_key,
                        "entity_label": ordered[-1]["entity_label"],
                        "metric": "purchase_count",
                        "forecast_value": round(point_purchases, 2),
                        "lower_bound": round(max(0.0, point_purchases * (1 - interval_width)), 2),
                        "upper_bound": round(point_purchases * (1 + interval_width), 2),
                        "history_days": history_days,
                        "model_name": "global_ar_mlp" if not sparse else "global_ar_mlp_coldstart",
                        "fallback_reason": "coldstart_history_sparse" if sparse else "",
                    }
                )
        else:
            # 数据样本极度稀疏时的防御性 Fallback 退化机制
            previous = ordered[-min(len(ordered), horizon * 2) : -horizon] if len(ordered) > horizon else []
            previous_gmv = _mean([float(row.get("gmv") or 0) for row in previous]) if previous else baseline_gmv
            change_rate = (baseline_gmv - previous_gmv) / previous_gmv if previous_gmv else 0.0
            for offset in range(1, horizon + 1):
                forecast_dt = max_dt + timedelta(days=offset)
                target_weekday = forecast_dt.weekday()
                same_weekday_views = [
                    float(row.get("views") or 0)
                    for row in ordered
                    if _parse_date(row["dt"]).weekday() == target_weekday
                ]
                expected_views = _mean(same_weekday_views[-4:]) if same_weekday_views else baseline_views
                views_covariate_factor = 1.0
                if baseline_views > 0:
                    views_covariate_factor = min(max(expected_views / baseline_views, 0.5), 2.0)
                
                multiplier = 1 + min(max(change_rate, -0.25), 0.25) * (offset / horizon)
                point_gmv = max(0.0, baseline_gmv * multiplier * views_covariate_factor)
                point_purchases = max(0.0, baseline_purchases * multiplier * views_covariate_factor)
                
                results.append(
                    {
                        "contract_version": FORECAST_CONTRACT_VERSION,
                        "dt": forecast_dt.isoformat(),
                        "scope": scope,
                        "entity_key": entity_key,
                        "entity_label": ordered[-1]["entity_label"],
                        "metric": "gmv",
                        "forecast_value": round(point_gmv, 2),
                        "lower_bound": round(max(0.0, point_gmv * (1 - interval_width)), 2),
                        "upper_bound": round(point_gmv * (1 + interval_width), 2),
                        "history_days": history_days,
                        "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                        "fallback_reason": "insufficient_history_days" if sparse else "",
                    }
                )
                results.append(
                    {
                        "contract_version": FORECAST_CONTRACT_VERSION,
                        "dt": forecast_dt.isoformat(),
                        "scope": scope,
                        "entity_key": entity_key,
                        "entity_label": ordered[-1]["entity_label"],
                        "metric": "purchase_count",
                        "forecast_value": round(point_purchases, 2),
                        "lower_bound": round(max(0.0, point_purchases * (1 - interval_width)), 2),
                        "upper_bound": round(point_purchases * (1 + interval_width), 2),
                        "history_days": history_days,
                        "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                        "fallback_reason": "insufficient_history_days" if sparse else "",
                    }
                )
    return results


def build_entity_rows(
    daily_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    history_by_entity = select_entities(daily_rows, int(config["top_entities"]))
    forecast_by_entity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in forecast_rows:
        forecast_by_entity.setdefault((row["scope"], row["entity_key"]), []).append(row)
    entities: list[dict[str, Any]] = []
    for key, history in history_by_entity.items():
        forecasts = forecast_by_entity.get(key, [])
        gmv_forecast = sum(float(row["forecast_value"]) for row in forecasts if row["metric"] == "gmv")
        purchase_forecast = sum(float(row["forecast_value"]) for row in forecasts if row["metric"] == "purchase_count")
        recent = sorted(history, key=lambda row: row["dt"])[-int(config["forecast_horizon_days"]) :]
        recent_gmv = sum(float(row.get("gmv") or 0) for row in recent)
        expected_change_rate = round((gmv_forecast - recent_gmv) / recent_gmv, 6) if recent_gmv else 0.0
        sparse = len({row["dt"] for row in history}) < int(config["min_history_days"])
        risk_level = _risk_level(expected_change_rate, sparse, config)
        entities.append(
            {
                "contract_version": FORECAST_CONTRACT_VERSION,
                "scope": key[0],
                "entity_key": key[1],
                "entity_label": history[-1]["entity_label"],
                "forecast_gmv": round(gmv_forecast, 2),
                "forecast_purchase_count": round(purchase_forecast, 2),
                "recent_gmv": round(recent_gmv, 2),
                "expected_change_rate": expected_change_rate,
                "history_days": len({row["dt"] for row in history}),
                "risk_level": risk_level,
                "risk_score": _risk_score(expected_change_rate, sparse),
                "model_name": "rolling_baseline" if not sparse else "sparse_baseline_fallback",
                "fallback_reason": "insufficient_history_days" if sparse else "",
                "recommended_action": _entity_action(risk_level, sparse),
            }
        )
    return sorted(entities, key=lambda row: (-int(row["risk_score"]), row["scope"], row["entity_key"]))


def build_backtest_rows(daily_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    backtest_window = max([int(config["backtest_window_days"]), *[int(value) for value in config.get("backtest_windows", [])]])
    for key, entity_rows in select_entities(daily_rows, int(config["top_entities"])).items():
        ordered = sorted(entity_rows, key=lambda row: row["dt"])
        if len(ordered) < 2:
            continue
        holdout = ordered[-min(backtest_window, len(ordered) - 1) :]
        train = ordered[: -len(holdout)]
        rolling_baseline = _mean([float(row.get("gmv") or 0) for row in train]) if train else float(ordered[0].get("gmv") or 0)
        for offset, row in enumerate(holdout, start=1):
            row_dt = _parse_date(row["dt"])
            historical = ordered[: ordered.index(row)]
            weekday_history = [
                float(history_row.get("gmv") or 0)
                for history_row in historical
                if _parse_date(history_row["dt"]).weekday() == row_dt.weekday()
            ]
            baseline = _mean(weekday_history[-4:]) if weekday_history else rolling_baseline
            model_name = "weekday_baseline_backtest" if weekday_history else "rolling_baseline_backtest"
            
            # 外生协变量修正：利用当天实际的 views 流量修正时序基准
            historical_views = [float(history_row.get("views") or 0) for history_row in historical]
            baseline_views = _mean(historical_views[-28:]) if historical_views else 0.0
            actual_views = float(row.get("views") or 0)
            
            views_covariate_factor = 1.0
            if baseline_views > 0:
                views_covariate_factor = min(max(actual_views / baseline_views, 0.5), 2.0)
            
            baseline = baseline * views_covariate_factor
            actual = float(row.get("gmv") or 0)
            error = actual - baseline
            rows.append(
                {
                    "contract_version": FORECAST_CONTRACT_VERSION,
                    "dt": row["dt"],
                    "scope": key[0],
                    "entity_key": key[1],
                    "entity_label": row["entity_label"],
                    "metric": "gmv",
                    "actual": round(actual, 2),
                    "forecast": round(baseline, 2),
                    "absolute_error": round(abs(error), 2),
                    "error": round(error, 2),
                    "horizon": offset,
                    "model_name": model_name + "_covariate" if baseline_views > 0 else model_name,
                }
            )
    return rows


def build_backtest_evaluation(backtest_rows: list[dict[str, Any]], config: dict[str, Any], run_id: str) -> dict[str, Any]:
    windows = sorted({int(value) for value in config.get("backtest_windows", []) if int(value) > 0})
    if not windows:
        windows = [int(config["backtest_window_days"])]
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "run_id": run_id,
        "windows": windows,
        "model_metrics": _aggregate_backtest(backtest_rows, lambda row: str(row["model_name"])),
        "horizon_metrics": _aggregate_backtest(backtest_rows, lambda row: f"h{int(row.get('horizon') or 1)}"),
        "window_metrics": [
            {
                "window_days": window,
                **_metric_summary([row for row in backtest_rows if int(row.get("horizon") or 1) <= window]),
            }
            for window in windows
        ],
        "error_distribution": {
            "max_absolute_error": max([float(row["absolute_error"]) for row in backtest_rows], default=0.0),
            "avg_absolute_error": round(_mean([float(row["absolute_error"]) for row in backtest_rows]), 6),
            "backtest_rows": len(backtest_rows),
        },
        "quality_gates": [
            {
                "name": "site_wape",
                "actual": _site_metric(backtest_rows, "wape"),
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": (_site_metric(backtest_rows, "wape") or 1.0) <= float(config["max_site_wape"]),
            },
            {
                "name": "weekday_baseline_available",
                "actual": any(row.get("model_name") == "weekday_baseline_backtest" for row in backtest_rows),
                "operator": "==",
                "expected": True,
                "passed": any(row.get("model_name") == "weekday_baseline_backtest" for row in backtest_rows),
            },
        ],
    }


def _aggregate_backtest(backtest_rows: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in backtest_rows:
        groups.setdefault(key_fn(row), []).append(row)
    return [{"group": key, **_metric_summary(rows)} for key, rows in sorted(groups.items())]


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual_sum = sum(float(row.get("actual") or 0) for row in rows)
    absolute_error_sum = sum(float(row.get("absolute_error") or 0) for row in rows)
    error_sum = sum(float(row.get("error") or 0) for row in rows)
    return {
        "rows": len(rows),
        "actual_sum": round(actual_sum, 2),
        "forecast_sum": round(sum(float(row.get("forecast") or 0) for row in rows), 2),
        "wape": round(absolute_error_sum / actual_sum, 6) if actual_sum else None,
        "bias": round(error_sum / actual_sum, 6) if actual_sum else None,
        "mae": round(absolute_error_sum / len(rows), 6) if rows else None,
    }


def _site_metric(backtest_rows: list[dict[str, Any]], metric: str) -> float | None:
    summary = _metric_summary([row for row in backtest_rows if row.get("scope") == "site"])
    return summary.get(metric)


def build_quality(
    daily_rows: list[dict[str, Any]],
    backtest_rows: list[dict[str, Any]],
    config: dict[str, Any],
    excluded_dates: list[str] | None = None,
    driver_history: dict[str, int] | None = None,
) -> dict[str, Any]:
    driver_history = driver_history or {
        "requested_history_days": int(config["history_collect_days"]),
        "collected_history_days": int(config["history_collect_days"]),
        "max_driver_history_rows": int(config["max_driver_history_rows"]),
        "driver_history_rows": len(daily_rows),
    }
    site_history_days = len({row["dt"] for row in daily_rows if row["scope"] == "site"})
    site_backtest = [row for row in backtest_rows if row["scope"] == "site"]
    actual_sum = sum(float(row["actual"]) for row in site_backtest)
    absolute_error_sum = sum(float(row["absolute_error"]) for row in site_backtest)
    error_sum = sum(float(row["error"]) for row in site_backtest)
    site_wape = round(absolute_error_sum / actual_sum, 6) if actual_sum else None
    site_bias = round(error_sum / actual_sum, 6) if actual_sum else None
    checks = [
        {
            "name": "minimum_history_days",
            "actual": site_history_days,
            "operator": ">=",
            "expected": int(config["min_history_days"]),
            "passed": site_history_days >= int(config["min_history_days"]),
        }
    ]
    checks.append(
        {
            "name": "driver_history_rows",
            "actual": int(driver_history["driver_history_rows"]),
            "operator": "<=",
            "expected": int(driver_history["max_driver_history_rows"]),
            "passed": int(driver_history["driver_history_rows"]) <= int(driver_history["max_driver_history_rows"]),
        }
    )
    if site_wape is not None:
        checks.append(
            {
                "name": "site_wape",
                "actual": site_wape,
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": site_wape <= float(config["max_site_wape"]),
            }
        )
    else:
        checks.append(
            {
                "name": "site_wape",
                "actual": 1.0,
                "operator": "<=",
                "expected": float(config["max_site_wape"]),
                "passed": False,
            }
        )
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "passed": all(check["passed"] for check in checks),
        "quality_status": "passed" if all(check["passed"] for check in checks) else "needs_review",
        "checks": checks,
        "metrics": {
            "site_history_days": site_history_days,
            "site_wape": site_wape,
            "site_bias": site_bias,
            "backtest_rows": len(backtest_rows),
            "sparse_history": site_history_days < int(config["min_history_days"]),
            "excluded_incomplete_dates": excluded_dates or [],
            **driver_history,
        },
    }


def build_risks(entity_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    for row in entity_rows:
        if row["risk_level"] == "low":
            continue
        risks.append(
            {
                "contract_version": FORECAST_CONTRACT_VERSION,
                "risk_id": f"forecast:{row['scope']}:{row['entity_key']}",
                "scope": row["scope"],
                "entity_key": row["entity_key"],
                "entity_label": row["entity_label"],
                "severity": row["risk_level"],
                "risk_type": "insufficient_history" if row["fallback_reason"] else "demand_drop",
                "metric": "gmv",
                "evidence": {
                    "expected_change_rate": row["expected_change_rate"],
                    "history_days": row["history_days"],
                    "forecast_gmv": row["forecast_gmv"],
                },
                "recommended_action": row["recommended_action"],
            }
        )
    return sorted(risks, key=lambda row: (0 if row["severity"] == "high" else 1, row["entity_key"]))


def build_summary(
    daily_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    entity_rows: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    quality: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    input_snapshot: dict[str, Any],
    driver_history: dict[str, int] | None = None,
) -> dict[str, Any]:
    site_forecast = [row for row in forecast_rows if row["scope"] == "site"]
    site_gmv = sum(float(row["forecast_value"]) for row in site_forecast if row["metric"] == "gmv")
    site_purchases = sum(float(row["forecast_value"]) for row in site_forecast if row["metric"] == "purchase_count")
    history_dates = sorted({row["dt"] for row in daily_rows if row["scope"] == "site"})
    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "run_id": run_id,
        "input_snapshot": input_snapshot,
        "forecast_horizon_days": int(config["forecast_horizon_days"]),
        "training_window_days": int(config["training_window_days"]),
        "backtest_window_days": int(config["backtest_window_days"]),
        "history_days": len(history_dates),
        "driver_history_rows": int((driver_history or {}).get("driver_history_rows") or 0),
        "max_driver_history_rows": int((driver_history or {}).get("max_driver_history_rows") or config["max_driver_history_rows"]),
        "history_range": {"min_dt": history_dates[0] if history_dates else None, "max_dt": history_dates[-1] if history_dates else None},
        "entity_count": len(entity_rows),
        "site_forecast_gmv": round(site_gmv, 2),
        "site_forecast_purchase_count": round(site_purchases, 2),
        "risk_count": len(risks),
        "high_risk_count": len([row for row in risks if row["severity"] == "high"]),
        "quality_status": quality["quality_status"],
        "top_risk": risks[0] if risks else None,
        "recommended_action": "Use forecast risks as planning signals; do not treat sparse-history forecasts as causal or high-confidence predictions.",
    }


def select_entities(rows: list[dict[str, Any]], top_entities: int) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["scope"], row["entity_key"]), []).append(row)
    category_scores = sorted(
        [
            (sum(float(row.get("gmv") or 0) for row in entity_rows), key)
            for key, entity_rows in grouped.items()
            if key[0] == "category"
        ],
        reverse=True,
    )
    keep = {("site", "all")}
    keep.update(key for _, key in category_scores[:top_entities])
    return {key: entity_rows for key, entity_rows in grouped.items() if key in keep}


def _risk_level(expected_change_rate: float, sparse: bool, config: dict[str, Any]) -> str:
    if sparse or expected_change_rate <= float(config["high_risk_drop_rate"]):
        return "high"
    if expected_change_rate <= float(config["medium_risk_drop_rate"]):
        return "medium"
    return "low"


def _risk_score(expected_change_rate: float, sparse: bool) -> int:
    if sparse:
        return 85
    return min(100, max(0, int(abs(min(expected_change_rate, 0)) * 400)))


def _entity_action(risk_level: str, sparse: bool) -> str:
    if sparse:
        return "Collect more history or reduce forecast granularity before committing spend."
    if risk_level == "high":
        return "Review merchandising plan, recommendation coverage, and experiment exposure before the forecast window."
    if risk_level == "medium":
        return "Monitor category demand and prepare a constrained promotion or recommendation adjustment."
    return "Use as baseline demand for planning."


def reconcile_hierarchical_forecasts(
    forecast_rows: list[dict[str, Any]],
    daily_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not forecast_rows:
        return forecast_rows

    # 1. 计算每个实体的历史均值以作为分配权重
    weights_db: dict[tuple[str, str, str], float] = {}
    grouped_history: dict[tuple[str, str, str], list[float]] = {}
    for row in daily_rows:
        scope = row["scope"]
        entity_key = row["entity_key"]
        grouped_history.setdefault((scope, entity_key, "gmv"), []).append(float(row.get("gmv") or 0.0))
        grouped_history.setdefault((scope, entity_key, "purchase_count"), []).append(float(row.get("purchase_count") or 0.0))
        
    for k, vals in grouped_history.items():
        weights_db[k] = _mean(vals[-28:])

    # 2. 将预测行按 (dt, metric) 分组
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in forecast_rows:
        by_group.setdefault((row["dt"], row["metric"]), []).append(row)

    reconciled_results: list[dict[str, Any]] = []

    for (dt, metric), group in by_group.items():
        # 3. 提取全站与各大品类的预测行
        site_rows = [r for r in group if r["scope"] == "site"]
        category_rows = [r for r in group if r["scope"] == "category"]

        if not site_rows or not category_rows:
            reconciled_results.extend(group)
            continue

        site_row = site_rows[0]
        site_val = float(site_row["forecast_value"])
        sum_category_val = sum(float(c["forecast_value"]) for c in category_rows)

        # 4. 计算大盘预测值与各品类预测和之间的加总偏差
        bias = site_val - sum_category_val

        # 5. 获取各品类权重的非负权重基准
        cat_weights = []
        for c in category_rows:
            w = weights_db.get((c["scope"], c["entity_key"], metric), 0.0)
            cat_weights.append(max(0.0, w))

        total_weight = sum(cat_weights)
        
        # 6. 对各品类预测行进行误差对齐与上下界按比例自适应缩放
        for idx, c in enumerate(category_rows):
            w_norm = cat_weights[idx] / total_weight if total_weight > 0 else 1.0 / len(category_rows)
            old_val = float(c["forecast_value"])
            new_val = max(0.0, old_val + w_norm * bias)
            c["forecast_value"] = round(new_val, 2)
            
            # 上下界自适应对齐调节
            if old_val > 0:
                ratio = new_val / old_val
                c["lower_bound"] = round(max(0.0, float(c["lower_bound"]) * ratio), 2)
                c["upper_bound"] = round(float(c["upper_bound"]) * ratio, 2)
            else:
                delta = w_norm * bias
                c["lower_bound"] = round(max(0.0, float(c["lower_bound"]) + delta), 2)
                c["upper_bound"] = round(max(0.0, float(c["upper_bound"]) + delta), 2)

        # 7. 重新校准顶层 Site 预测行，保证严格的加总一致性
        site_row["forecast_value"] = round(sum(float(c["forecast_value"]) for c in category_rows), 2)
        site_row["lower_bound"] = round(sum(float(c["lower_bound"]) for c in category_rows), 2)
        site_row["upper_bound"] = round(sum(float(c["upper_bound"]) for c in category_rows), 2)

        reconciled_results.extend(site_rows)
        reconciled_results.extend(category_rows)

    return reconciled_results


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
