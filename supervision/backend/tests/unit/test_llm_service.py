from __future__ import annotations

from application.usecases.generate_report import GenerateReportUseCase
from infrastructure.llm.providers.base_provider import LLMProvider
from infrastructure.llm.services.llm_service import LLMService
from scripts.generate_demo_report import generate_demo_report


class RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.last_prompt: str | None = None

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
        self.last_prompt = prompt
        return "路况平稳：检测到 1 辆车通过 main_gate，速度约 5.1 km/h。"

    def get_model_name(self) -> str:
        return "recording-provider"


def test_llm_service_builds_report_from_frame_report_json() -> None:
    provider = RecordingProvider()
    service = LLMService(provider=provider)

    result = service.generate_traffic_report(
        generate_demo_report(),
        location_label="学校门口",
        scene_tags=["school_zone"],
    )

    assert result.provider == "recording-provider"
    assert "main_gate" in result.report_markdown
    assert "dynamic_context" in (provider.last_prompt or "")
    assert "school_zone" in (provider.last_prompt or "")
    assert result.input_summary["total_in"] == 1
    assert result.dynamic_context["scene"]["location_label"] == "学校门口"


def test_llm_service_rule_based_fallback_without_provider() -> None:
    service = LLMService()

    result = service.generate_traffic_report(generate_demo_report())

    assert result.provider == "rule-based-local"
    assert "累计进入 1" in result.report_markdown
    assert result.input_summary["active_tracks"] == 1
    assert result.dynamic_context["physical_state"]["active_tracks"] == 1


def test_generate_report_use_case_accepts_injected_llm_service() -> None:
    provider = RecordingProvider()
    use_case = GenerateReportUseCase(LLMService(provider=provider))

    result = use_case.execute(generate_demo_report(), location_label="学校门口")

    assert result.provider == "recording-provider"
    assert provider.last_prompt is not None
