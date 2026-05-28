from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from infrastructure.llm.providers.base_provider import LLMProvider


@dataclass(frozen=True)
class TrafficReportResult:
    provider: str
    report_markdown: str
    input_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "report_markdown": self.report_markdown,
            "input_summary": self.input_summary,
        }


class LLMService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def generate_traffic_report(self, stats: dict[str, Any]) -> TrafficReportResult:
        input_summary = self._summarize_input(stats)
        if self.provider is None:
            return TrafficReportResult(
                provider="rule-based-local",
                report_markdown=self._build_rule_based_report(input_summary),
                input_summary=input_summary,
            )

        prompt = self._build_prompt(stats)
        report = self.provider.generate(prompt)
        return TrafficReportResult(
            provider=self.provider.get_model_name(),
            report_markdown=report,
            input_summary=input_summary,
        )

    @staticmethod
    def _summarize_input(stats: dict[str, Any]) -> dict[str, Any]:
        active_tracks = stats.get("active_tracks", [])
        zone_stats = stats.get("zone_stats", [])
        speeds = [
            float(track["speed_kmh"])
            for track in active_tracks
            if track.get("speed_kmh") is not None
        ]
        avg_speed = sum(speeds) / len(speeds) if speeds else None
        return {
            "frame_index": stats.get("frame_index"),
            "active_tracks": len(active_tracks),
            "total_in": int(stats.get("total_in", 0)),
            "total_out": int(stats.get("total_out", 0)),
            "avg_speed_kmh": avg_speed,
            "zones": [zone.get("name", "unknown") for zone in zone_stats],
        }

    @staticmethod
    def _build_prompt(stats: dict[str, Any]) -> str:
        return (
            "你是交通路况分析助手。请根据以下 FrameReport JSON 输出中文路况解析，"
            "包含流量、速度、异常风险和管理建议。\n\n"
            f"{json.dumps(stats, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_rule_based_report(summary: dict[str, Any]) -> str:
        avg_speed = summary["avg_speed_kmh"]
        speed_text = "暂无速度数据" if avg_speed is None else f"平均速度约 {avg_speed:.1f} km/h"
        return (
            "## 路况解析\n\n"
            f"- 当前活跃目标 {summary['active_tracks']} 个，累计进入 {summary['total_in']}，"
            f"累计离开 {summary['total_out']}。\n"
            f"- {speed_text}。\n"
            f"- 监控区域：{', '.join(summary['zones']) or '未配置'}。\n"
            "- 当前 demo 数据未显示拥堵或异常速度，适合作为课设展示的基础闭环。"
        )
