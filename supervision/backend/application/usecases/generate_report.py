from __future__ import annotations

from typing import Any

from infrastructure.llm.services.llm_service import LLMService, TrafficReportResult


class GenerateReportUseCase:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def execute(self, stats: dict[str, Any]) -> TrafficReportResult:
        return self.llm_service.generate_traffic_report(stats)
