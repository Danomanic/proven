"""Tests for the CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from proven.config import APIKeys, Config
from proven.main import app, get_provider, get_runner

runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help and basic commands."""

    def test_help_shows_app_info(self):
        """Test that --help shows application info."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "proven" in result.output.lower() or "test" in result.output.lower()

    def test_generate_help(self):
        """Test that generate --help works."""
        result = runner.invoke(app, ["generate", "--help"])

        assert result.exit_code == 0
        assert "generate" in result.output.lower()

    def test_config_help(self):
        """Test that config --help works."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0

    def test_init_help(self):
        """Test that init --help works."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0


class TestConfigCommands:
    """Tests for config CLI commands."""

    def test_config_show(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test config show command."""
        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "provider" in result.output.lower()

    def test_config_set_provider(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test setting provider via CLI."""
        result = runner.invoke(app, ["config", "set", "provider", "openai"])

        assert result.exit_code == 0
        assert "openai" in result.output.lower()

    def test_config_set_test_framework(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test setting test framework via CLI."""
        result = runner.invoke(app, ["config", "set", "test-framework", "jest"])

        assert result.exit_code == 0
        assert "jest" in result.output.lower()

    def test_config_set_invalid_key(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test setting invalid config key."""
        result = runner.invoke(app, ["config", "set", "invalid-key", "value"])

        assert result.exit_code == 1


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_config_file(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test that init creates a project config file."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (temp_cwd / ".proven.yaml").exists()

    def test_init_with_provider(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test init with custom provider."""
        result = runner.invoke(app, ["init", "--provider", "openai"])

        assert result.exit_code == 0

        import yaml

        with open(temp_cwd / ".proven.yaml") as f:
            config = yaml.safe_load(f)

        assert config["provider"] == "openai"

    def test_init_with_framework(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test init with custom framework."""
        result = runner.invoke(app, ["init", "--test-framework", "jest"])

        assert result.exit_code == 0

        import yaml

        with open(temp_cwd / ".proven.yaml") as f:
            config = yaml.safe_load(f)

        assert config["test_framework"] == "jest"


class TestGetProvider:
    """Tests for the get_provider helper function."""

    def test_get_provider_claude(self):
        """Test getting Claude provider."""
        config = Config(
            provider="claude",
            api_keys=APIKeys(anthropic="test-key"),
        )

        with patch("proven.main.get_api_key_with_prompt", return_value="test-key"):
            with patch("proven.providers.anthropic.anthropic"):
                provider = get_provider(config)

        assert provider.name == "anthropic"

    def test_get_provider_openai(self):
        """Test getting OpenAI provider."""
        config = Config(
            provider="openai",
            api_keys=APIKeys(openai="test-key"),
        )

        with patch("proven.main.get_api_key_with_prompt", return_value="test-key"):
            with patch("proven.providers.openai.openai"):
                provider = get_provider(config)

        assert provider.name == "openai"

    def test_get_provider_ollama(self):
        """Test getting Ollama provider."""
        config = Config(provider="ollama")

        with patch("proven.main.get_api_key_with_prompt", return_value=None):
            provider = get_provider(config)

        assert provider.name == "ollama"

    def test_get_provider_invalid(self):
        """Test getting invalid provider raises error."""
        config = Config(provider="invalid")

        with patch("proven.main.get_api_key_with_prompt", return_value=None):
            with pytest.raises(Exception):
                get_provider(config)


class TestGetRunner:
    """Tests for the get_runner helper function."""

    def test_get_runner_pytest(self):
        """Test getting pytest runner."""
        config = Config(test_framework="pytest")
        runner = get_runner(config)

        assert runner.name == "pytest"

    def test_get_runner_jest(self):
        """Test getting Jest runner."""
        config = Config(test_framework="jest")
        runner = get_runner(config)

        assert runner.name == "jest"

    def test_get_runner_maven(self):
        """Test getting Maven runner."""
        config = Config(test_framework="maven")
        runner = get_runner(config)

        assert runner.name == "maven"

    def test_get_runner_invalid(self):
        """Test getting invalid runner raises error."""
        config = Config(test_framework="invalid")

        with pytest.raises(Exception):
            get_runner(config)


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_requires_description(self):
        """Test that generate requires a description argument."""
        result = runner.invoke(app, ["generate"])

        assert result.exit_code != 0

    @patch("proven.main.get_provider")
    @patch("proven.main.get_runner")
    @patch("proven.main.TDDEngine")
    @patch("proven.main.load_config")
    def test_generate_runs_tdd_workflow(
        self,
        mock_load_config,
        mock_engine_class,
        mock_get_runner,
        mock_get_provider,
        temp_home: Path,
        temp_cwd: Path,
    ):
        """Test that generate runs the TDD workflow."""
        # Setup mocks
        mock_load_config.return_value = Config(api_keys=APIKeys(anthropic="test-key"))
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        mock_runner = MagicMock()
        mock_runner.name = "pytest"
        mock_get_runner.return_value = mock_runner

        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.final_test_result.is_green = True
        mock_result.test_file = temp_cwd / "test.py"
        mock_result.source_file = temp_cwd / "src.py"

        # Create async mock for run
        async def mock_run(*args, **kwargs):
            return mock_result

        mock_engine.run = mock_run
        mock_engine_class.return_value = mock_engine

        runner.invoke(
            app,
            ["generate", "Create an add function", "--yes"],
        )

        # Should have attempted to run
        mock_engine_class.assert_called_once()


class TestAPIKeyPrompt:
    """Tests for API key prompting."""

    def test_get_api_key_with_prompt_returns_existing(self):
        """Test that existing API key is returned without prompting."""
        from proven.main import get_api_key_with_prompt

        config = Config(api_keys=APIKeys(anthropic="existing-key"))

        with patch("proven.main.Prompt") as mock_prompt:
            key = get_api_key_with_prompt(config, "claude")

        assert key == "existing-key"
        mock_prompt.ask.assert_not_called()

    def test_get_api_key_with_prompt_ollama_no_key(self):
        """Test that Ollama doesn't require API key."""
        from proven.main import get_api_key_with_prompt

        config = Config()

        with patch("proven.main.Prompt") as mock_prompt:
            key = get_api_key_with_prompt(config, "ollama")

        assert key is None
        mock_prompt.ask.assert_not_called()
