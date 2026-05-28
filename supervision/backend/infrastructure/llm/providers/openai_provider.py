from __future__ import annotations

import httpx
from openai import OpenAI
from openai import OpenAI as OpenAIClient

from infrastructure.llm.providers.base_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model
        self._client: OpenAIClient | None = None

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
        response = self._get_client().responses.create(
            model=self.model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.output_text

    def get_model_name(self) -> str:
        return self.model

    def _get_client(self) -> OpenAIClient:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                http_client=httpx.Client(trust_env=False),
            )
        return self._client
