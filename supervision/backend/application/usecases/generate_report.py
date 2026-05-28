from __future__ import annotations

from typing import Any

from infrastructure.llm.provider_factory import build_llm_provider
from infrastructure.llm.services.llm_service import LLMService, TrafficReportResult
from shared.configs.settings import Settings


class GenerateReportUseCase:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService(
            provider=build_llm_provider(Settings().llm),
        )

    def execute(
        self,
        stats: dict[str, Any],
        location_label: str | None = None,
        scene_tags: list[str] | None = None,
    ) -> TrafficReportResult:
        return self.llm_service.generate_traffic_report(
            stats,
            location_label=location_label,
            scene_tags=scene_tags,
        )
