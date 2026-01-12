"""Ollama local model provider implementation."""

import json
from typing import AsyncIterator, Optional

import httpx

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Provider for local Ollama models."""

    DEFAULT_MODEL = "codellama"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.base_url = base_url or self.DEFAULT_BASE_URL

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response using Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()["response"]

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Stream a response using Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        if system:
            payload["system"] = system

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
