from __future__ import annotations

from shared.configs.settings import LLMConfig

from infrastructure.llm.providers.base_provider import LLMProvider
from infrastructure.llm.providers.openai_provider import OpenAIProvider


def build_llm_provider(config: LLMConfig) -> LLMProvider | None:
    if not config.enabled or not config.openai_api_key:
        return None
    return OpenAIProvider(api_key=config.openai_api_key, model=config.model)
