from __future__ import annotations

from spark_jobs.decision_maker import build_decision_manifest


def test_decision_maker_intervention():
    # 构造模拟的雷达异常警报数据
    anomaly_alerts = [
        {
            "severity": "critical",
            "direction": "drop",
            "entity_type": "product",
            "entity_id": "product_1001",
            "entity_label": "apple_iphone",
            "metric": "revenue",
            "robust_z": 8.5
        },
        {
            "severity": "critical",
            "direction": "drop",
            "entity_type": "category",
            "entity_id": "electronics",
            "entity_label": "electronics",
            "metric": "revenue",
            "robust_z": 7.2
        },
        {
            "severity": "warning",  # 警告级异常不应触发紧急拦截干预
            "direction": "drop",
            "entity_type": "product",
            "entity_id": "product_1002",
            "entity_label": "shoes",
            "metric": "purchases",
            "robust_z": 3.8
        }
    ]

    manifest = build_decision_manifest(
        anomaly_alerts=anomaly_alerts,
        optimization_plan=[],
        forecasting_entities=[],
        run_id="test-run-1"
    )

    interventions = manifest["intervention_decisions"]
    # 应当生成 2 项干预决策（1项商品挂起，1项品类审计）
    assert len(interventions) == 2
    
    suspend_action = [i for i in interventions if i["decision_type"] == "emergency_suspend"][0]
    assert suspend_action["target_id"] == "product_1001"
    assert suspend_action["evidence_score"] == 8.5
    
    audit_action = [i for i in interventions if i["decision_type"] == "price_audit"][0]
    assert audit_action["target_id"] == "electronics"
    assert audit_action["evidence_score"] == 7.2


def test_decision_maker_restock():
    # 构造模拟的优化计划促销数据 (views=100, purchases=10, avg_price=100.0, baseline_gmv=1000.0, expected_incremental_purchases=5.0)
    optimization_plan = [
        {
            "product_id": "prod_2001",
            "brand": "xiaomi",
            "category_level1": "electronics",
            "action": "promo_high",
            "views": 100,
            "purchases": 10,
            "avg_price": 100.0,
            "baseline_gmv": 1000.0,
            "expected_incremental_purchases": 5.0  # 预计增量购买数 5
        }
    ]

    # 1. 模拟周转库存 = purchases * 1.0 = 10
    # 2. 未来 7 天预期基础销量 = baseline_gmv / avg_price = 10
    # 3. 未来总预期需求 = 基准(10) + 增量(5) = 15
    # 4. 预期需求(15) > 初始库存(10)，触发补货
    # 5. 建议补货量 = 预期需求(15) * 1.5 - 当前库存(10) = 22.5 - 10 = 12.5，向上取整为 13
    # 6. 到货天数 (electronics 类别为 4 天)
    # 7. 进货成本 = 13 * 100.0 * 0.6 = 780.0

    manifest = build_decision_manifest(
        anomaly_alerts=[],
        optimization_plan=optimization_plan,
        forecasting_entities=[],
        run_id="test-run-2"
    )

    restocks = manifest["restock_decisions"]
    assert len(restocks) == 1
    
    decision = restocks[0]
    assert decision["product_id"] == "prod_2001"
    assert decision["current_stock"] == 10
    assert decision["forecasted_demand"] == 15.0
    assert decision["reorder_qty"] == 13
    assert decision["estimated_cost"] == 780.0
    assert decision["lead_time_days"] == 4
    assert decision["supplier"] == "Electronics_Wholesale_Corp"


def test_decision_maker_dynamic_safety_stock():
    # 构造模拟的优化计划促销数据
    optimization_plan = [
        {
            "product_id": "prod_3001",
            "brand": "samsung",
            "category_level1": "electronics",
            "action": "promo_high",
            "views": 100,
            "purchases": 10,
            "avg_price": 100.0,
            "baseline_gmv": 1000.0,
            "expected_incremental_purchases": 5.0
        }
    ]
    # 构造模拟的雷达警报：prod_3001 触发了 views 指标的突增警报 (direction='spike')
    anomaly_alerts = [
        {
            "severity": "warning",
            "direction": "spike",
            "entity_type": "product",
            "entity_id": "prod_3001",
            "entity_label": "samsung_galaxy",
            "metric": "views",
            "robust_z": 5.5
        }
    ]

    # 1. 模拟周转库存 = purchases * 1.0 = 10
    # 2. 未来 7 天预期基础销量 = baseline_gmv / avg_price = 10
    # 3. 未来总预测销量 = 10 + 5 = 15
    # 4. 因触发 spike 预警，安全库存系数调至 2.5
    # 5. 建议补货量 = 预期销量(15) * 2.5 - 当前库存(10) = 37.5 - 10 = 27.5，向上取整为 28
    # 6. electronics 常规到货期是 4 天，因是 spike 商品，加急缩短为 3 天
    # 7. 进货成本 = 28 * 100.0 * 0.6 = 1680.0
    # 8. rush_order 应标记为 True

    manifest = build_decision_manifest(
        anomaly_alerts=anomaly_alerts,
        optimization_plan=optimization_plan,
        forecasting_entities=[],
        run_id="test-run-3"
    )

    restocks = manifest["restock_decisions"]
    assert len(restocks) == 1
    
    decision = restocks[0]
    assert decision["product_id"] == "prod_3001"
    assert decision["reorder_qty"] == 28
    assert decision["estimated_cost"] == 1680.0
    assert decision["lead_time_days"] == 3
    assert decision["rush_order"] is True
    assert "自动上调安全库存水位至 2.5 倍" in decision["reason"]
