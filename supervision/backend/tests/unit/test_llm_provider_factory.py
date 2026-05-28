from __future__ import annotations

from infrastructure.llm.provider_factory import build_llm_provider
from infrastructure.llm.providers.openai_provider import OpenAIProvider
from shared.configs.settings import LLMConfig


def test_llm_provider_factory_returns_none_when_disabled() -> None:
    config = LLMConfig(LLM_ENABLED=False, OPENAI_API_KEY="test-key")

    assert build_llm_provider(config) is None


def test_llm_provider_factory_returns_none_without_api_key() -> None:
    config = LLMConfig(LLM_ENABLED=True, OPENAI_API_KEY="")

    assert build_llm_provider(config) is None


def test_llm_provider_factory_builds_openai_provider_when_enabled() -> None:
    config = LLMConfig(
        LLM_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="gpt-4o-mini",
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, OpenAIProvider)
    assert provider.get_model_name() == "gpt-4o-mini"
