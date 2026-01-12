"""Anthropic Claude provider implementation."""

from typing import AsyncIterator, Optional

import anthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response using Claude."""
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Stream a response using Claude."""
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
