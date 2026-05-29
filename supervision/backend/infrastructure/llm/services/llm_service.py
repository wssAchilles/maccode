from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from application.services.context_assembler import DynamicContextAssembler

from infrastructure.llm.providers.base_provider import LLMProvider


@dataclass(frozen=True)
class TrafficReportResult:
    provider: str
    report_markdown: str
    input_summary: dict[str, Any]
    dynamic_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "report_markdown": self.report_markdown,
            "input_summary": self.input_summary,
            "dynamic_context": self.dynamic_context,
        }


class LLMService:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        context_assembler: DynamicContextAssembler | None = None,
    ) -> None:
        self.provider = provider
        self.context_assembler = context_assembler or DynamicContextAssembler()

    def generate_traffic_report(
        self,
        stats: dict[str, Any],
        location_label: str | None = None,
        scene_tags: list[str] | None = None,
    ) -> TrafficReportResult:
        dynamic_context = self.context_assembler.assemble(
            stats,
            location_label=location_label,
            scene_tags=scene_tags,
        )
        dynamic_payload = dynamic_context.to_prompt_payload()
        input_summary = dynamic_payload["physical_state"]
        if self.provider is None:
            return TrafficReportResult(
                provider="rule-based-local",
                report_markdown=self._build_rule_based_report(dynamic_payload),
                input_summary=input_summary,
                dynamic_context=dynamic_payload,
            )

        prompt = self._build_prompt(stats, dynamic_payload)
        report = self.provider.generate(prompt)
        return TrafficReportResult(
            provider=self.provider.get_model_name(),
            report_markdown=report,
            input_summary=input_summary,
            dynamic_context=dynamic_payload,
        )

    @staticmethod
    def _build_prompt(stats: dict[str, Any], dynamic_context: dict[str, Any]) -> str:
        return (
            "你是端云协同空间智能系统中的云端交通认知 Agent。"
            "请基于 dynamic_context 与原始 FrameReport JSON 输出中文路况解析，"
            "严格区分观测事实、风险推理和干预建议。\n\n"
            "dynamic_context:\n"
            f"{json.dumps(dynamic_context, ensure_ascii=False, indent=2)}\n\n"
            "frame_report:\n"
            f"{json.dumps(stats, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_rule_based_report(dynamic_context: dict[str, Any]) -> str:
        summary = dynamic_context["physical_state"]
        scene = dynamic_context["scene"]
        risks = dynamic_context["risk_signals"]
        avg_speed = summary["avg_speed_kmh"]
        speed_text = "暂无速度数据" if avg_speed is None else f"平均速度约 {avg_speed:.1f} km/h"
        calibration_text = summary.get("calibration_quality") or "未提供"
        traffic_flow = summary.get("traffic_flow") or {}
        congestion_level = (
            traffic_flow.get("congestion_level", "未提供")
            if isinstance(traffic_flow, dict)
            else "未提供"
        )
        regional_people = summary.get("regional_people_count") or {}
        density_text = "未提供"
        if isinstance(regional_people, dict):
            density = regional_people.get("density_people_per_sqm")
            people_count = regional_people.get("people_count")
            method = regional_people.get("estimation_method", "unknown")
            if density is not None:
                density_text = (
                    f"{float(density):.2f} 人/m²，人数约 {people_count}，模型 {method}"
                )
        infrastructure = summary.get("infrastructure_semantics") or {}
        signal_text = "未检测到信号灯"
        if isinstance(infrastructure, dict) and infrastructure.get("traffic_light_count", 0):
            signal_text = (
                f"{infrastructure.get('traffic_light_state', 'unknown')}，"
                f"红灯候选目标 {infrastructure.get('red_light_violation_candidate_track_ids', [])}"
            )
        risk_text = "、".join(risk["type"] for risk in risks)
        recommendation = (
            "建议立即复核红灯/超速/拥挤证据并触发人工处置。"
            if any(risk.get("severity") in {"critical", "high"} for risk in risks)
            else "当前未显示高危事件，可继续观察交通流变化。"
        )
        tag_text = ", ".join(scene["scene_tags"]) or "未标注"
        return (
            "## 路况解析\n\n"
            f"- 场景：{scene['location_label']}；标签：{tag_text}。\n"
            f"- 当前活跃目标 {summary['active_tracks']} 个，累计进入 {summary['total_in']}，"
            f"累计离开 {summary['total_out']}。\n"
            f"- {speed_text}。\n"
            f"- 标定质量：{calibration_text}；交通流状态：{congestion_level}。\n"
            f"- 人群密度：{density_text}。\n"
            f"- 信号灯语义：{signal_text}。\n"
            f"- 监控区域：{', '.join(summary['zones']) or '未配置'}。\n"
            f"- 风险信号：{risk_text}。\n"
            f"- 处置建议：{recommendation}"
        )
