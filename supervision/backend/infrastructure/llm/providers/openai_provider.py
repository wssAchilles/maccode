from __future__ import annotations

from openai import OpenAI

from infrastructure.llm.providers.base_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
        response = self._client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.output_text

    def get_model_name(self) -> str:
        return self.model
