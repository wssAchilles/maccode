from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError
