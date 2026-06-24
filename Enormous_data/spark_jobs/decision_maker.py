from __future__ import annotations

import math
from typing import Any

DECISION_CONTRACT_VERSION = "auto-decision-governance/v1"


def build_decision_manifest(
    anomaly_alerts: list[dict[str, Any]] | None,
    optimization_plan: list[dict[str, Any]] | None,
    forecasting_entities: list[dict[str, Any]] | None,
    run_id: str,
) -> dict[str, Any]:
    """根据异常雷达的 critical 报警和优化模块的促销 Lift 增量，自适应生成自动拦截干预和预测性补货单。"""
    anomaly_alerts = anomaly_alerts or []
    optimization_plan = optimization_plan or []
    forecasting_entities = forecasting_entities or []

    # 1. 异常联动干预控制（雷达下架与调价安全阀）
    intervention_decisions: list[dict[str, Any]] = []
    for alert in anomaly_alerts:
        # 仅针对严重（critical）且销量/销售额发生暴跌（drop）的异常行为触发干预
        if alert.get("severity") == "critical" and alert.get("direction") == "drop":
            entity_type = alert.get("entity_type")
            entity_id = alert.get("entity_id")
            entity_label = alert.get("entity_label")
            metric = alert.get("metric")
            robust_z = alert.get("robust_z") or 0.0

            if metric in {"revenue", "purchases"}:
                if entity_type == "product":
                    # 单品级销量严重暴跌，触发“紧急下架/暂挂”决策以防止缺货或标价异常
                    intervention_decisions.append({
                        "decision_type": "emergency_suspend",
                        "target_type": "product",
                        "target_id": str(entity_id),
                        "target_label": entity_label,
                        "metric": metric,
                        "evidence_score": float(robust_z),
                        "reason": "商品级销量严重异动暴跌，疑似标错价、BUG或缺货，自动执行防御性挂起",
                        "recommended_action": "下架该商品并人工核查系统价格与真实库存"
                    })
                elif entity_type == "category":
                    # 类目级销售骤降，触发“价格/系统安全审计”
                    intervention_decisions.append({
                        "decision_type": "price_audit",
                        "target_type": "category",
                        "target_id": str(entity_id),
                        "target_label": entity_label,
                        "metric": metric,
                        "evidence_score": float(robust_z),
                        "reason": "品类级销售额剧烈崩塌，疑似推荐引擎失效或全局支付故障",
                        "recommended_action": "启动整条品类支付漏斗与活动配置安全排查"
                    })
            elif metric in {"conversion_rate", "view_to_purchase_rate"}:
                # 转化率严重突降，触发“漏斗诊断”
                intervention_decisions.append({
                    "decision_type": "funnel_check",
                    "target_type": "product" if entity_type == "product" else "category",
                    "target_id": str(entity_id),
                    "target_label": entity_label,
                    "metric": metric,
                    "evidence_score": float(robust_z),
                    "reason": "转化率出现特大跌幅，可能存在详情页加载失败或结算按钮故障",
                    "recommended_action": "通知前端与测序团队对该页面漏斗转化进行灰度验证"
                })

    # 2. 预测性智能供应链补货建议（补货自动流）
    restock_decisions: list[dict[str, Any]] = []
    
    # 收集在雷达中触发 views 或 purchases/revenue 突增（spike）的商品 ID 集合
    spike_product_ids: set[str] = set()
    for alert in anomaly_alerts:
        if alert.get("entity_type") == "product" and alert.get("direction") == "spike":
            if alert.get("metric") in {"views", "purchases", "revenue"}:
                spike_product_ids.add(str(alert.get("entity_id")))
    
    # 建立品类的预测增长系数索引以备使用
    cat_change_rate: dict[str, float] = {}
    for entity in forecasting_entities:
        if entity.get("scope") == "category":
            cat_change_rate[entity["entity_key"]] = float(entity.get("expected_change_rate") or 0.0)

    for item in optimization_plan:
        product_id = str(item["product_id"])
        brand = item.get("brand") or "unknown"
        category = item.get("category_level1") or "unknown"
        action_name = item.get("action") or "none"
        
        views = float(item.get("views") or 0.0)
        purchases = float(item.get("purchases") or 0.0)
        avg_price = float(item.get("avg_price") or 0.0)
        
        if avg_price <= 0 or purchases <= 0:
            continue

        # 判定该商品是否正在经历雷达检测到的流量/销量突增
        is_spike = product_id in spike_product_ids
        # 突发暴增异动期安全库存系数自适应临时上调至 2.5，其余为 1.5 默认值
        safety_coefficient = 2.5 if is_spike else 1.5

        # 模拟当前紧张的水位：将过去历史 purchases 量的 1.0 倍作为目前周转库存
        current_stock = int(purchases * 1.0)
        
        # 计算未来无促销下的基准预测 purchases：通过 baseline_gmv 换算未来 7 天基本 purchases
        baseline_gmv = float(item.get("baseline_gmv") or (views * (purchases / max(1.0, views)) * avg_price))
        future_baseline_purchases = baseline_gmv / avg_price
        
        # 获取促销增量销量 purchases
        incremental_purchases = float(item.get("expected_incremental_purchases") or 0.0)
        
        # 联动预测：最终未来 7 天预期总购买数 = 基准销量 + 促销增量
        forecasted_demand = future_baseline_purchases + incremental_purchases
        
        # 若“未来预期总销量 > 当前库存水位”，则自适应触发补货决策
        if forecasted_demand > current_stock:
            # 补货量 = 预期总销量 * 动态安全库存系数 - 当前周转库存
            restock_qty = int(math.ceil(forecasted_demand * safety_coefficient - current_stock))
            restock_qty = max(1, restock_qty)
            
            # 补货进货成本（设为建议售价的 60%）
            restock_cost = round(restock_qty * avg_price * 0.6, 2)
            
            # 分品类指定合理的到货期 (lead time) 与模拟供应商
            lead_time_days = 3
            supplier_name = "Standard_Supplier_Group"
            if "electr" in category.lower():
                lead_time_days = 4
                supplier_name = "Electronics_Wholesale_Corp"
            elif "apparel" in category.lower() or "shoes" in category.lower():
                lead_time_days = 2
                supplier_name = "Fast_Fashion_Apparel_Inc"
            elif "med" in category.lower() or "cosmet" in category.lower():
                lead_time_days = 3
                supplier_name = "Bio_Pharma_Logistics"

            # 大促加急：对于流量/销量异动突发商品，缩短到货天数（如减 1 天，最小为 1）并标记加急
            if is_spike:
                lead_time_days = max(1, lead_time_days - 1)

            restock_decisions.append({
                "product_id": product_id,
                "brand": brand,
                "category": category,
                "marketing_action": action_name,
                "current_stock": current_stock,
                "forecasted_demand": round(forecasted_demand, 2),
                "reorder_qty": restock_qty,
                "estimated_cost": restock_cost,
                "supplier": supplier_name,
                "lead_time_days": lead_time_days,
                "rush_order": is_spike,
                "reason": f"由于雷达检测到销量/流量突增且促销活动（{action_name}）带来增量需求，自动上调安全库存水位至 {safety_coefficient} 倍进行加急备货" if is_spike else f"由于促销活动（{action_name}）带来增量需求，库存水位不足以支撑未来预期销量",
            })

    # 按补货成本从高到低排序，帮助采购理清轻重缓急
    restock_decisions = sorted(restock_decisions, key=lambda d: -d["estimated_cost"])

    return {
        "contract_version": DECISION_CONTRACT_VERSION,
        "run_id": run_id,
        "summary": {
            "intervention_count": len(intervention_decisions),
            "restock_order_count": len(restock_decisions),
            "total_estimated_restock_cost": round(sum(d["estimated_cost"] for d in restock_decisions), 2),
        },
        "intervention_decisions": intervention_decisions,
        "restock_decisions": restock_decisions,
    }
