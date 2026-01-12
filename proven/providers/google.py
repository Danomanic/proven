"""Google Gemini provider implementation."""

from typing import AsyncIterator, Optional

from google import genai
from google.genai import types

from .base import LLMProvider


class GoogleProvider(LLMProvider):
    """Provider for Google Gemini models."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return "google"

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response using Gemini."""
        config = None
        if system:
            config = types.GenerateContentConfig(system_instruction=system)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Stream a response using Gemini."""
        config = None
        if system:
            config = types.GenerateContentConfig(system_instruction=system)

        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
