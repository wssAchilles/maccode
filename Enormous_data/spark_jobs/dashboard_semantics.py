from __future__ import annotations

from typing import Any


DASHBOARD_CUBE_ALL_VALUE = "__all__"
DASHBOARD_CUBE_CONTRACT_VERSION = "dashboard-metric-cube/v1"
DASHBOARD_SEMANTIC_VERSION = "dashboard-semantic-metrics/v1"


def dashboard_metric_definitions(run_id: str) -> list[dict[str, Any]]:
    return [
        _metric(
            run_id,
            metric_name="event_count",
            chinese_name="事件量",
            aggregation="计数",
            formula="符合筛选条件的行为事件行数",
            quality_assertions=["非负", "物化汇总层与清洗明细层行数一致"],
        ),
        _metric(
            run_id,
            metric_name="purchase_count",
            chinese_name="购买数",
            aggregation="条件计数",
            formula="行为类型为购买的事件行数",
            quality_assertions=["非负", "购买数不超过事件量"],
        ),
        _metric(
            run_id,
            metric_name="total_sales",
            chinese_name="成交额",
            aggregation="条件求和",
            formula="购买事件的价格合计",
            quality_assertions=["非负", "仅购买行为计入金额"],
        ),
        _metric(
            run_id,
            metric_name="unique_users",
            chinese_name="去重用户数",
            aggregation="去重计数",
            formula="筛选粒度内去重后的用户数量",
            quality_assertions=["按查询粒度预聚合，避免跨分组重复相加"],
        ),
        _metric(
            run_id,
            metric_name="unique_sessions",
            chinese_name="去重会话数",
            aggregation="去重计数",
            formula="筛选粒度内去重后的会话数量",
            quality_assertions=["按查询粒度预聚合，避免跨分组重复相加"],
        ),
        _metric(
            run_id,
            metric_name="avg_order_value",
            chinese_name="客单价",
            aggregation="派生指标",
            formula="成交额 / 购买数",
            quality_assertions=["购买数为零时返回 0", "金额保留两位小数"],
        ),
    ]


def _metric(
    run_id: str,
    *,
    metric_name: str,
    chinese_name: str,
    aggregation: str,
    formula: str,
    quality_assertions: list[str],
) -> dict[str, Any]:
    return {
        "contract_version": DASHBOARD_SEMANTIC_VERSION,
        "run_id": run_id,
        "metric_name": metric_name,
        "chinese_name": chinese_name,
        "grain": "筛选维度汇总 / 日级趋势",
        "source": "dashboard_metric_cube",
        "refresh_frequency": "随 Spark 批处理刷新",
        "aggregation": aggregation,
        "formula": formula,
        "quality_assertions": quality_assertions,
    }
