"""Shared test fixtures for Proven."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from proven.config import APIKeys, Config, OllamaConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_home(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary home directory."""
    home = temp_dir / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def temp_cwd(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary working directory."""
    cwd = temp_dir / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    return cwd


@pytest.fixture
def sample_config() -> Config:
    """Create a sample configuration."""
    return Config(
        provider="claude",
        model="claude-sonnet-4-20250514",
        test_framework="pytest",
        test_directory="tests",
        source_directory="src",
        api_keys=APIKeys(
            anthropic="test-anthropic-key",
            openai="test-openai-key",
            google="test-google-key",
        ),
        ollama=OllamaConfig(
            base_url="http://localhost:11434",
            model="codellama",
        ),
    )


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "mock"
    provider.generate = AsyncMock(return_value="```python\ndef test_example():\n    assert True\n```")
    provider.stream = AsyncMock()
    return provider


@pytest.fixture
def mock_test_runner(temp_cwd: Path) -> MagicMock:
    """Create a mock test runner."""
    from proven.runners.base import TestResult

    runner = MagicMock()
    runner.name = "pytest"
    runner.working_dir = temp_cwd

    # Default to failing first, then passing
    runner.run = MagicMock(
        side_effect=[
            TestResult(success=False, output="FAILED", passed=0, failed=1, errors=0),
            TestResult(success=True, output="PASSED", passed=1, failed=0, errors=0),
        ]
    )
    return runner


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove API keys from environment."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
