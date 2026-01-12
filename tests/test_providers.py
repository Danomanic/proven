"""Tests for LLM providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proven.providers.anthropic import AnthropicProvider
from proven.providers.base import LLMProvider
from proven.providers.google import GoogleProvider
from proven.providers.ollama import OllamaProvider
from proven.providers.openai import OpenAIProvider


class TestLLMProviderBase:
    """Tests for the base LLM provider interface."""

    def test_base_class_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()


class TestAnthropicProvider:
    """Tests for the Anthropic Claude provider."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch("proven.providers.anthropic.anthropic"):
            provider = AnthropicProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.model == AnthropicProvider.DEFAULT_MODEL
        assert provider.name == "anthropic"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch("proven.providers.anthropic.anthropic"):
            provider = AnthropicProvider(api_key="test-key", model="claude-opus-4-20250514")

        assert provider.model == "claude-opus-4-20250514"

    @pytest.mark.asyncio
    async def test_generate_calls_api(self):
        """Test generate method calls the Anthropic API."""
        with patch("proven.providers.anthropic.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Generated code")]
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key")
            result = await provider.generate("Write a function", "System prompt")

            assert result == "Generated code"
            mock_client.messages.create.assert_called_once()


class TestOpenAIProvider:
    """Tests for the OpenAI GPT provider."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch("proven.providers.openai.openai"):
            provider = OpenAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.model == OpenAIProvider.DEFAULT_MODEL
        assert provider.name == "openai"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch("proven.providers.openai.openai"):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        assert provider.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_calls_api(self):
        """Test generate method calls the OpenAI API."""
        with patch("proven.providers.openai.openai") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Generated code"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.AsyncOpenAI.return_value = mock_client

            provider = OpenAIProvider(api_key="test-key")
            result = await provider.generate("Write a function", "System prompt")

            assert result == "Generated code"
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_includes_system_prompt(self):
        """Test that system prompt is included in messages."""
        with patch("proven.providers.openai.openai") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Code"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.AsyncOpenAI.return_value = mock_client

            provider = OpenAIProvider(api_key="test-key")
            await provider.generate("Write code", "Be helpful")

            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "Be helpful"
            assert messages[1]["role"] == "user"


class TestGoogleProvider:
    """Tests for the Google Gemini provider."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch("proven.providers.google.genai"):
            provider = GoogleProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.model == GoogleProvider.DEFAULT_MODEL
        assert provider.name == "google"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch("proven.providers.google.genai"):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")

        assert provider.model == "gemini-1.5-pro"


class TestOllamaProvider:
    """Tests for the Ollama local provider."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        provider = OllamaProvider()

        assert provider.model == OllamaProvider.DEFAULT_MODEL
        assert provider.base_url == OllamaProvider.DEFAULT_BASE_URL
        assert provider.name == "ollama"

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        provider = OllamaProvider(
            model="llama2",
            base_url="http://custom:11434",
        )

        assert provider.model == "llama2"
        assert provider.base_url == "http://custom:11434"

    @pytest.mark.asyncio
    async def test_generate_calls_api(self):
        """Test generate method calls the Ollama API."""
        with patch("proven.providers.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Generated code"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            provider = OllamaProvider()
            result = await provider.generate("Write a function")

            assert result == "Generated code"

    def test_no_api_key_required(self):
        """Test that Ollama doesn't require an API key."""
        provider = OllamaProvider()
        assert provider.api_key is None
