"""Tests for the configuration module."""

from pathlib import Path

import pytest
import yaml

from proven.config import (
    Config,
    OllamaConfig,
    _resolve_env_vars,
    _resolve_env_vars_in_dict,
    get_global_config_path,
    get_project_config_path,
    load_config,
    save_global_config,
    save_project_config,
)


class TestConfig:
    """Tests for the Config model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.provider == "claude"
        assert config.model is None
        assert config.test_framework == "pytest"
        assert config.test_directory == "tests"
        assert config.source_directory == "src"

    def test_get_api_key_claude(self, sample_config: Config):
        """Test getting API key for Claude."""
        assert sample_config.get_api_key("claude") == "test-anthropic-key"
        assert sample_config.get_api_key("anthropic") == "test-anthropic-key"

    def test_get_api_key_openai(self, sample_config: Config):
        """Test getting API key for OpenAI."""
        assert sample_config.get_api_key("openai") == "test-openai-key"
        assert sample_config.get_api_key("gpt") == "test-openai-key"

    def test_get_api_key_google(self, sample_config: Config):
        """Test getting API key for Google."""
        assert sample_config.get_api_key("google") == "test-google-key"
        assert sample_config.get_api_key("gemini") == "test-google-key"

    def test_get_api_key_unknown_provider(self, sample_config: Config):
        """Test getting API key for unknown provider returns None."""
        assert sample_config.get_api_key("unknown") is None

    def test_get_model_for_provider_default(self):
        """Test getting default model for each provider."""
        config = Config()

        assert "claude" in config.get_model_for_provider("claude")
        assert "gpt" in config.get_model_for_provider("openai")
        assert "gemini" in config.get_model_for_provider("google")

    def test_get_model_for_provider_override(self):
        """Test model override takes precedence."""
        config = Config(model="custom-model")

        assert config.get_model_for_provider("claude") == "custom-model"
        assert config.get_model_for_provider("openai") == "custom-model"

    def test_get_model_for_provider_ollama(self):
        """Test Ollama uses its own model config."""
        config = Config(ollama=OllamaConfig(model="llama2"))

        assert config.get_model_for_provider("ollama") == "llama2"


class TestEnvVarResolution:
    """Tests for environment variable resolution."""

    def test_resolve_env_vars_simple(self, monkeypatch: pytest.MonkeyPatch):
        """Test resolving a simple environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")

        result = _resolve_env_vars("${TEST_VAR}")
        assert result == "test_value"

    def test_resolve_env_vars_with_text(self, monkeypatch: pytest.MonkeyPatch):
        """Test resolving env var embedded in text."""
        monkeypatch.setenv("API_KEY", "secret123")

        result = _resolve_env_vars("Bearer ${API_KEY}")
        assert result == "Bearer secret123"

    def test_resolve_env_vars_missing(self):
        """Test resolving missing env var returns empty string."""
        result = _resolve_env_vars("${NONEXISTENT_VAR}")
        assert result == ""

    def test_resolve_env_vars_in_dict(self, monkeypatch: pytest.MonkeyPatch):
        """Test resolving env vars in a dictionary."""
        monkeypatch.setenv("KEY1", "value1")
        monkeypatch.setenv("KEY2", "value2")

        data = {
            "simple": "${KEY1}",
            "nested": {
                "key": "${KEY2}",
            },
            "unchanged": "literal",
        }

        result = _resolve_env_vars_in_dict(data)

        assert result["simple"] == "value1"
        assert result["nested"]["key"] == "value2"
        assert result["unchanged"] == "literal"


class TestConfigPaths:
    """Tests for configuration file paths."""

    def test_global_config_path(self, temp_home: Path):
        """Test global config path is in home directory."""
        path = get_global_config_path()

        assert path == temp_home / ".proven" / "config.yaml"

    def test_project_config_path(self, temp_cwd: Path):
        """Test project config path is in current directory."""
        path = get_project_config_path()

        # Resolve both paths to handle macOS /private/var vs /var symlinks
        assert path.resolve() == (temp_cwd / ".proven.yaml").resolve()


class TestConfigLoading:
    """Tests for loading configuration."""

    def test_load_config_defaults(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test loading config with no files returns defaults."""
        config = load_config()

        assert config.provider == "claude"
        assert config.test_framework == "pytest"

    def test_load_config_from_global(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test loading config from global file."""
        global_config_dir = temp_home / ".proven"
        global_config_dir.mkdir(parents=True)

        config_data = {
            "provider": "openai",
            "test_framework": "jest",
        }

        with open(global_config_dir / "config.yaml", "w") as f:
            yaml.safe_dump(config_data, f)

        config = load_config()

        assert config.provider == "openai"
        assert config.test_framework == "jest"

    def test_load_config_project_overrides_global(self, temp_home: Path, temp_cwd: Path, clean_env):
        """Test project config overrides global config."""
        # Create global config
        global_config_dir = temp_home / ".proven"
        global_config_dir.mkdir(parents=True)

        with open(global_config_dir / "config.yaml", "w") as f:
            yaml.safe_dump({"provider": "openai", "test_framework": "jest"}, f)

        # Create project config
        with open(temp_cwd / ".proven.yaml", "w") as f:
            yaml.safe_dump({"provider": "claude"}, f)

        config = load_config()

        # Provider from project, framework from global
        assert config.provider == "claude"
        assert config.test_framework == "jest"

    def test_load_config_from_env_vars(self, temp_home: Path, temp_cwd: Path, monkeypatch: pytest.MonkeyPatch):
        """Test API keys are loaded from environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic-key")
        monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

        config = load_config()

        assert config.api_keys.anthropic == "env-anthropic-key"
        assert config.api_keys.openai == "env-openai-key"


class TestConfigSaving:
    """Tests for saving configuration."""

    def test_save_global_config(self, temp_home: Path, sample_config: Config):
        """Test saving global configuration."""
        save_global_config(sample_config)

        global_path = temp_home / ".proven" / "config.yaml"
        assert global_path.exists()

        with open(global_path) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["provider"] == "claude"
        assert saved_data["test_framework"] == "pytest"

    def test_save_project_config(self, temp_cwd: Path, sample_config: Config):
        """Test saving project configuration."""
        save_project_config(sample_config)

        project_path = temp_cwd / ".proven.yaml"
        assert project_path.exists()

        with open(project_path) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["provider"] == "claude"

    def test_save_global_config_creates_directory(self, temp_home: Path):
        """Test saving global config creates the directory if needed."""
        config = Config(provider="openai")

        save_global_config(config)

        assert (temp_home / ".proven").exists()
        assert (temp_home / ".proven" / "config.yaml").exists()
