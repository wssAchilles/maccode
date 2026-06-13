from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.benchmark_evidence import BenchmarkEvidenceService


class OptimizationImpactService:
    def __init__(self, project_root: str | Path, cache_dir: str | Path):
        self.project_root = Path(project_root)
        self.cache_dir = Path(cache_dir)

    def load(self) -> dict[str, Any]:
        evidence = BenchmarkEvidenceService(self.project_root).load()
        metrics = {
            name: self._load_metric(name, {})
            for name in (
                "summary",
                "feature_mart_summary",
                "feature_mart_freshness",
                "feature_mart_quality",
                "feature_mart_partitions",
                "recommendation_summary",
                "recommendation_quality",
                "forecasting_summary",
                "forecasting_quality",
                "anomaly_summary",
                "experiment_summary",
                "experiment_guardrails",
            )
        }
        data_layers = self._data_layers(evidence, metrics)
        quality_gates = self._quality_gates(metrics)
        model_cards = self._model_cards(metrics)
        performance_cards = self._performance_cards(evidence)
        counted_cards = data_layers + quality_gates + model_cards + performance_cards
        danger_count = sum(1 for card in counted_cards if card["tone"] == "danger")
        warning_count = sum(1 for card in counted_cards if card["tone"] == "warning")
        success_count = sum(1 for card in counted_cards if card["tone"] == "success")
        blocking_ids = {"feature-quality", "recommendation-gate", "forecast-backtest", "experiment-guardrails", "spark-task-health"}
        has_blocking_danger = any(card["tone"] == "danger" and card["id"] in blocking_ids for card in counted_cards)
        overall_tone = "danger" if has_blocking_danger else "warning" if danger_count or warning_count else "success"
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "overall_status": "healthy" if overall_tone == "success" else "needs_attention",
            "overall_tone": overall_tone,
            "headline": "优化计划已经转化为前端可见的数据层、质量门禁、模型可信度和 Spark 性能证据。",
            "summary": {
                "success_count": success_count,
                "warning_count": warning_count,
                "danger_count": danger_count,
                "visible_page_count": 4,
                "evidence_count": len(counted_cards),
                "primary_action": self._primary_action(overall_tone),
            },
            "data_layers": data_layers,
            "quality_gates": quality_gates,
            "model_cards": model_cards,
            "performance_cards": performance_cards,
            "frontend_sections": self._frontend_sections(overall_tone, metrics, evidence),
        }

    def _load_metric(self, name: str, default: Any) -> Any:
        path = self.cache_dir / f"{name}.json"
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default

    def _data_layers(self, evidence: dict[str, Any], metrics: dict[str, Any]) -> list[dict[str, str]]:
        hdfs_inputs = evidence.get("hdfs_inputs") or []
        feature_summary = _dict(metrics["feature_mart_summary"])
        feature_quality = _dict(metrics["feature_mart_quality"])
        partitions = _dict(metrics["feature_mart_partitions"])
        expected = _number(partitions.get("expected"))
        written = _number(partitions.get("written"))
        missing = partitions.get("missing") if isinstance(partitions.get("missing"), list) else []
        partition_tone = "success" if expected and written == expected and not missing else "warning" if expected else "danger"
        loaded_artifacts = sum(1 for value in metrics.values() if value)
        return [
            _card(
                "hdfs-inputs",
                "HDFS/Parquet 输入",
                "ready" if hdfs_inputs else "missing",
                "success" if hdfs_inputs else "warning",
                f"{len(hdfs_inputs)} paths",
                "前端运维页可以直接看到正式 benchmark 使用的 CSV 与 Parquet 输入。",
                "保留 1%/5% 样本和 Parquet 路径，方便复现实验。",
            ),
            _card(
                "feature-mart",
                "清洗后 Feature Mart",
                str(feature_summary.get("quality_status") or feature_quality.get("quality_status") or "pending"),
                _tone(feature_summary.get("quality_status") or feature_quality.get("quality_status")),
                _format_number(feature_summary.get("deduped_event_rows") or feature_quality.get("deduped_event_rows") or feature_quality.get("cleaned_rows")),
                "清洗、去重和隔离后的事件数据作为推荐、预测、异常和实验模块的统一输入。",
                f"隔离率 {_format_percent(feature_quality.get('quarantined_rate'))}",
            ),
            _card(
                "feature-partitions",
                "分区写入",
                "passed" if partition_tone == "success" else "needs_review",
                partition_tone,
                f"{_format_number(written)}/{_format_number(expected)}",
                "按日期分区后，前端可展示分区覆盖、缺失分区和数据时间范围。",
                f"{partitions.get('min_dt', 'pending')} -> {partitions.get('max_dt', 'pending')}",
            ),
            _card(
                "metric-cache",
                "前端指标缓存",
                "ready" if loaded_artifacts else "missing",
                "success" if loaded_artifacts else "danger",
                f"{loaded_artifacts} artifacts",
                "Flask API 读取稳定的缓存产物，前端刷新不再依赖每次实时 Spark 计算。",
                "Dashboard、Ops、推荐和预测页共用同一批证据。",
            ),
        ]

    def _quality_gates(self, metrics: dict[str, Any]) -> list[dict[str, str]]:
        feature_quality = _dict(metrics["feature_mart_quality"])
        freshness = _dict(metrics["feature_mart_freshness"])
        recommendation = _dict(metrics["recommendation_quality"])
        forecasting = _dict(metrics["forecasting_quality"])
        experiment = _dict(metrics["experiment_guardrails"])
        forecasting_metrics = _dict(forecasting.get("metrics"))
        return [
            _card(
                "feature-quality",
                "数据清洗门禁",
                str(feature_quality.get("quality_status") or "pending"),
                _tone(feature_quality.get("quality_status")),
                _format_percent(feature_quality.get("quarantined_rate")),
                "重复事件、非法事件类型、缺失关键字段和异常价格在发布前被量化。",
                f"{len(feature_quality.get('checks') or [])} 项检查",
            ),
            _card(
                "feature-freshness",
                "新鲜度 SLA",
                str(freshness.get("sla_status") or "pending"),
                _tone(freshness.get("sla_status")),
                _format_hours(freshness.get("freshness_lag_hours")),
                "前端能标记历史样本与当前时间的差距，避免把离线样本误读成实时生产流。",
                f"水位 {freshness.get('watermark_time', 'pending')}",
            ),
            _card(
                "recommendation-gate",
                "推荐发布门禁",
                str(recommendation.get("quality_status") or ("passed" if recommendation.get("passed") else "pending")),
                _tone(recommendation.get("quality_status") or recommendation.get("passed")),
                f"覆盖率 {_format_percent(recommendation.get('coverage_rate'))}",
                "覆盖率、兜底占比、置信度、重复和非法商品共同决定推荐能否在前端发布。",
                f"兜底占比 {_format_percent(recommendation.get('fallback_rate'))}",
            ),
            _card(
                "forecast-backtest",
                "预测回测门禁",
                str(forecasting.get("quality_status") or ("passed" if forecasting.get("passed") else "pending")),
                _tone(forecasting.get("quality_status") or forecasting.get("passed")),
                _format_ratio(forecasting_metrics.get("site_wape")),
                "用历史覆盖、加权绝对百分比误差、系统性偏差和稀疏兜底标记预测是否只适合作为方向性信号。",
                f"历史 {_format_number(forecasting_metrics.get('site_history_days'))} 天",
            ),
            _card(
                "experiment-guardrails",
                "实验护栏",
                str(experiment.get("status") or "pending"),
                _tone(experiment.get("status")),
                f"{len(experiment.get('checks') or [])} 项检查",
                "实验分流、样本量和推荐覆盖作为上线前护栏，避免离线估计被直接当作因果结论。",
                str(experiment.get("recommended_action") or "等待实验护栏。"),
            ),
        ]

    def _model_cards(self, metrics: dict[str, Any]) -> list[dict[str, str]]:
        recommendation_summary = _dict(metrics["recommendation_summary"])
        forecasting_summary = _dict(metrics["forecasting_summary"])
        anomaly_summary = _dict(metrics["anomaly_summary"])
        experiment_summary = _dict(metrics["experiment_summary"])
        return [
            _card(
                "recommendation-release",
                "推荐模块",
                str(recommendation_summary.get("quality_status") or "pending"),
                _tone(recommendation_summary.get("quality_status")),
                f"{_format_number(recommendation_summary.get('recommendation_count'))} 条推荐",
                f"覆盖 {_format_number(recommendation_summary.get('covered_sessions'))} 个会话，前端展示兜底占比与置信度风险。",
                f"平均置信度 {_format_percent(recommendation_summary.get('avg_confidence'))}",
            ),
            _card(
                "forecast-planning",
                "预测模块",
                str(forecasting_summary.get("quality_status") or "pending"),
                _tone(forecasting_summary.get("quality_status")),
                _format_money(forecasting_summary.get("site_forecast_gmv")),
                f"{_format_number(forecasting_summary.get('entity_count'))} 个实体，{_format_number(forecasting_summary.get('high_risk_count'))} 个高风险。",
                str(forecasting_summary.get("recommended_action") or "等待预测建议。"),
            ),
            _card(
                "anomaly-radar",
                "异常雷达",
                str(anomaly_summary.get("radar_status") or "pending"),
                _tone(anomaly_summary.get("radar_status")),
                f"严重 {_format_number(anomaly_summary.get('critical_count'))}",
                f"监控 {_format_number(anomaly_summary.get('monitored_entities'))} 个实体，把异常峰值在前端显性化。",
                str(_dict(anomaly_summary.get("top_alert")).get("recommended_action") or "持续观察异常队列。"),
            ),
            _card(
                "growth-experiment",
                "实验模块",
                str(experiment_summary.get("guardrail_status") or "pending"),
                _tone(experiment_summary.get("guardrail_status")),
                _format_money(experiment_summary.get("expected_incremental_gmv")),
                f"{_format_number(experiment_summary.get('assigned_users'))} users，分流 {_format_percent(experiment_summary.get('treatment_split'))}。",
                str(experiment_summary.get("causal_caveat") or "实验上线仍需随机留出组验证。"),
            ),
        ]

    def _performance_cards(self, evidence: dict[str, Any]) -> list[dict[str, str]]:
        summary = _dict(evidence.get("benchmark_summary"))
        history = _dict(evidence.get("history_summary"))
        module_rows = evidence.get("module_benchmark_runs") if isinstance(evidence.get("module_benchmark_runs"), list) else []
        successful_modules = sum(1 for row in module_rows if _dict(row).get("success"))
        speedup = _number(summary.get("yarn_only_to_algorithm_speedup"))
        failed_tasks = _number(history.get("failed_task_count")) or 0
        retried_tasks = _number(history.get("retried_task_count")) or 0
        return [
            _card(
                "spark-acceleration",
                "AQE + 算法护栏",
                "improved" if speedup and speedup > 1 else "pending",
                "success" if speedup and speedup > 1 else "warning",
                f"{speedup:.2f}x" if speedup else "pending",
                "相对 YARN-only CSV，算法护栏和 Spark 配置优化让运行耗时更可控。",
                str(summary.get("interpretation") or "等待 Spark benchmark。"),
            ),
            _card(
                "spark-task-health",
                "Spark 任务健康",
                "passed" if failed_tasks == 0 else "failed",
                "success" if failed_tasks == 0 else "danger",
                f"{_format_number(failed_tasks)} failed",
                "History event log 汇总失败任务、重试任务、shuffle 和 spill，用于解释前端性能表现。",
                f"retried {_format_number(retried_tasks)}",
            ),
            _card(
                "parquet-scale-path",
                "5% Parquet 路径",
                "ready" if summary.get("five_pct_parquet_elapsed_seconds") else "pending",
                "success" if summary.get("five_pct_parquet_elapsed_seconds") else "warning",
                _format_seconds(summary.get("five_pct_parquet_elapsed_seconds")),
                "前端可以展示 CSV 与 Parquet 的规模化实验边界，说明优化不是只在 smoke 数据上成立。",
                f"algorithm CSV {_format_seconds(summary.get('five_pct_algorithm_elapsed_seconds'))}",
            ),
            _card(
                "module-benchmark",
                "典型模块 benchmark",
                "passed" if module_rows and successful_modules == len(module_rows) else "pending",
                "success" if module_rows and successful_modules == len(module_rows) else "warning",
                f"{successful_modules}/{len(module_rows)}",
                "推荐、关联、异常和实验模块都有典型样本耗时证据，便于前端解释模块成本。",
                "20 万行代表性样本。",
            ),
        ]

    @staticmethod
    def _frontend_sections(overall_tone: str, metrics: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, str]]:
        recommendation = _dict(metrics["recommendation_summary"])
        forecasting = _dict(metrics["forecasting_summary"])
        benchmark_summary = _dict(evidence.get("benchmark_summary"))
        return [
            {
                "id": "dashboard",
                "page": "Dashboard",
                "route": "/",
                "tone": overall_tone,
                "status": "visible",
                "visible_result": "首页新增优化影响总览，用户一进入系统就能看到优化后的质量、性能和模型可信度。",
                "source_cards": "data_layers, quality_gates, performance_cards",
            },
            {
                "id": "ops",
                "page": "Ops",
                "route": "/ops",
                "tone": "success" if benchmark_summary else "warning",
                "status": "visible",
                "visible_result": "运维页展示 Spark 加速、History 任务健康、HDFS/Parquet 输入和模块 benchmark。",
                "source_cards": "performance_cards",
            },
            {
                "id": "recommendations",
                "page": "推荐守护",
                "route": "/recommendations",
                "tone": _tone(recommendation.get("quality_status")),
                "status": str(recommendation.get("quality_status") or "pending"),
                "visible_result": "推荐页显示发布门禁、兜底占比、置信度、回滚快照和推荐数量。",
                "source_cards": "recommendation-release, recommendation-gate",
            },
            {
                "id": "forecasting",
                "page": "需求预测",
                "route": "/forecasting",
                "tone": _tone(forecasting.get("quality_status")),
                "status": str(forecasting.get("quality_status") or "pending"),
                "visible_result": "预测页显示回测门禁、稀疏历史兜底、高风险实体和未来成交额信号。",
                "source_cards": "forecast-planning, forecast-backtest",
            },
        ]

    @staticmethod
    def _primary_action(overall_tone: str) -> str:
        if overall_tone == "success":
            return "可以把当前缓存作为演示与答辩主证据。"
        if overall_tone == "danger":
            return "先处理失败门禁，再展示优化收益。"
        return "优化收益已经可见，同时需要在前端保留风险提示。"


def _card(card_id: str, title: str, status: str, tone: str, metric: str, detail: str, action: str) -> dict[str, str]:
    return {
        "id": card_id,
        "title": title,
        "status": status,
        "tone": tone,
        "metric": metric,
        "detail": detail,
        "action": action,
    }


def _tone(status: Any) -> str:
    if isinstance(status, bool):
        return "success" if status else "danger"
    normalized = str(status or "").lower()
    if normalized in {"passed", "pass", "success", "succeeded", "healthy", "ready", "ok", "clear", "collected", "written"}:
        return "success"
    if normalized in {"failed", "failure", "danger", "critical", "high", "rejected", "blocked"}:
        return "danger"
    return "warning"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_number(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "pending"
    return f"{int(number):,}" if number.is_integer() else f"{number:,.2f}"


def _format_percent(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "pending"
    ratio = number * 100 if abs(number) <= 1 else number
    return f"{ratio:.1f}%"


def _format_ratio(value: Any) -> str:
    number = _number(value)
    return f"{number:.4f}" if number is not None else "pending"


def _format_hours(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "pending"
    return f"{number:.1f}h"


def _format_seconds(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "pending"
    return f"{number:.1f}s"


def _format_money(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "pending"
    return f"¥{number:,.2f}"
