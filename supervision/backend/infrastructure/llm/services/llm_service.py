from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.services.context_assembler import DynamicContextAssembler

from infrastructure.cognition.prompts import PromptAssembler
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
        prompt_assembler: PromptAssembler | None = None,
    ) -> None:
        self.provider = provider
        self.context_assembler = context_assembler or DynamicContextAssembler()
        self.prompt_assembler = prompt_assembler or PromptAssembler()

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

        messages = self.prompt_assembler.build_messages(
            stats,
            dynamic_payload,
            location_label=location_label,
            scene_tags=scene_tags,
        )
        report = self.provider.generate(messages)
        return TrafficReportResult(
            provider=self.provider.get_model_name(),
            report_markdown=report,
            input_summary=input_summary,
            dynamic_context=dynamic_payload,
        )

    @staticmethod
    def _build_rule_based_report(dynamic_context: dict[str, Any]) -> str:
        summary = dynamic_context["physical_state"]
        scene = dynamic_context["scene"]
        risks = dynamic_context["risk_signals"]
        avg_speed = summary["avg_speed_kmh"]
        calibration_text = summary.get("calibration_quality") or "未提供"
        traffic_flow = summary.get("traffic_flow") or {}
        congestion_level = (
            traffic_flow.get("congestion_level", "未提供")
            if isinstance(traffic_flow, dict)
            else "未提供"
        )
        space_mean_speed = (
            traffic_flow.get("space_mean_speed_kmh") if isinstance(traffic_flow, dict) else None
        )
        vehicle_density = (
            traffic_flow.get("density_k_veh_per_km") if isinstance(traffic_flow, dict) else None
        )
        regional_people = summary.get("regional_people_count") or {}
        density_text = "未提供"
        crowding_text = "未提供"
        if isinstance(regional_people, dict):
            density = regional_people.get("density_people_per_sqm")
            people_count = regional_people.get("people_count")
            method = regional_people.get("estimation_method", "unknown")
            if density is not None:
                density_text = (
                    f"每平方米约 **{float(density):.2f} 人**，人数约 **{people_count}**；"
                    f"这代表通行空间正在变窄，模型来源为 {method}"
                )
            crowding_level = regional_people.get("crowding_level")
            if crowding_level:
                crowding_text = (
                    f"{crowding_level}，表示人群密集程度会影响疏散速度和通行阻塞风险"
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
        speed_markdown = (
            "暂无可信速度数据"
            if avg_speed is None
            else (
                f"车辆整体移动速度约 **{avg_speed:.1f} km/h**；这不是像素位移，"
                "而是系统把画面运动换算到真实道路后的通行速度，可用来判断道路是否顺畅"
            )
        )
        flow_speed_text = (
            "未提供"
            if space_mean_speed is None
            else (
                f"整条道路车辆整体移动速度约 **{float(space_mean_speed):.1f} km/h**，"
                "可反映当前是顺畅、排队还是拥堵"
            )
        )
        vehicle_density_text = (
            "未提供"
            if vehicle_density is None
            else (
                f"每公里道路约 **{float(vehicle_density):.1f} 辆车**，数值越高越容易形成拥堵波"
            )
        )
        calibration_explanation = (
            f"标定质量为 **{calibration_text}**，表示系统正在把画面像素位置映射到真实地面距离，"
            "因此速度和轨迹判断的可信度会随标定质量变化"
        )
        return (
            f"📍 场景分析：{scene['location_label']}；标签：{tag_text}。\n\n"
            "## 感知摘要\n\n"
            f"- 当前活跃目标 **{summary['active_tracks']}** 个，累计进入 "
            f"**{summary['total_in']}**，累计离开 **{summary['total_out']}**。\n"
            f"- {speed_markdown}。\n"
            f"- {calibration_explanation}；交通流状态：**{congestion_level}**。\n"
            f"- 道路整体速度：{flow_speed_text}。\n"
            f"- 车辆密集程度：{vehicle_density_text}。\n"
            f"- 人群密度：**{density_text}**。\n"
            f"- 拥挤等级：{crowding_text}。\n"
            f"- 信号灯语义：{signal_text}。\n\n"
            "## 风险评估与预警\n\n"
            "| 维度 | 当前研判 |\n"
            "| --- | --- |\n"
            f"| 监控区域 | {', '.join(summary['zones']) or '未配置'} |\n"
            f"| 风险信号 | {risk_text} |\n"
            f"| Model 6 / 标定 | {calibration_explanation} |\n"
            "| 速度可信边界 | 若某条轨迹被判为 physics_valid=false，说明该速度可能受遮挡、"
            "跟踪跳变或标定不足影响，不能作为确定性告警依据。 |\n"
            "| 地面网格含义 | 半透明地面网格相当于给监控画面铺了一把真实世界的尺子，"
            "用来把画面中的移动换算成米和公里每小时。 |\n\n"
            f"🚨 综合研判：{risk_text}。\n\n"
            "## 决策建议\n\n"
            f"1. 💡 {recommendation}\n"
            "2. 💡 持续复核速度判断是否稳定：如果置信区间只在几公里每小时内波动，"
            "说明系统对速度判断较稳；如果区间变宽，应优先人工复核。\n"
            "3. 💡 若风险信号升级为 high/critical，立即转入人工处置流程。"
        )
