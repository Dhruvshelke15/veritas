from functools import lru_cache
from typing import Protocol

from anthropic import Anthropic

from app.config import settings


class Generator(Protocol):
    def generate(self, system: str, user_message: str) -> str: ...


class ClaudeGenerator:
    def __init__(self, client: Anthropic | None = None) -> None:
        self._client = client or Anthropic()

    def generate(self, system: str, user_message: str) -> str:
        response = self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        parts = [block.text for block in response.content if block.type == "text"]
        return "".join(parts)


@lru_cache(maxsize=1)
def get_generator() -> ClaudeGenerator:
    return ClaudeGenerator()
