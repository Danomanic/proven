"""Configuration management for Proven."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    """Ollama-specific configuration."""

    base_url: str = "http://localhost:11434"
    model: str = "codellama"


class APIKeys(BaseModel):
    """API key configuration with environment variable support."""

    anthropic: Optional[str] = None
    openai: Optional[str] = None
    google: Optional[str] = None


class Config(BaseModel):
    """Main configuration model."""

    provider: str = Field(default="claude", description="LLM provider to use")
    model: Optional[str] = Field(default=None, description="Model override")
    test_framework: str = Field(default="pytest", description="Test framework")
    test_directory: str = Field(default="tests", description="Test output directory")
    source_directory: str = Field(default="src", description="Source output directory")
    api_keys: APIKeys = Field(default_factory=APIKeys)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider, resolving env vars."""
        key_map = {
            "claude": self.api_keys.anthropic,
            "anthropic": self.api_keys.anthropic,
            "openai": self.api_keys.openai,
            "gpt": self.api_keys.openai,
            "google": self.api_keys.google,
            "gemini": self.api_keys.google,
        }
        return key_map.get(provider.lower())

    def get_model_for_provider(self, provider: str) -> str:
        """Get the model name for a provider."""
        if self.model:
            return self.model

        defaults = {
            "claude": "claude-sonnet-4-20250514",
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "gpt": "gpt-4o",
            "google": "gemini-2.0-flash",
            "gemini": "gemini-2.0-flash",
            "ollama": self.ollama.model,
        }
        return defaults.get(provider.lower(), "claude-sonnet-4-20250514")


def _resolve_env_vars(value: str) -> str:
    """Resolve environment variables in a string like ${VAR_NAME}."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, value)


def _resolve_env_vars_in_dict(d: dict) -> dict:
    """Recursively resolve environment variables in a dictionary."""
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = _resolve_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _resolve_env_vars_in_dict(value)
        else:
            result[key] = value
    return result


def get_global_config_path() -> Path:
    """Get the path to the global config file."""
    return Path.home() / ".proven" / "config.yaml"


def get_project_config_path() -> Path:
    """Get the path to the project-level config file."""
    return Path.cwd() / ".proven.yaml"


def load_config() -> Config:
    """Load configuration from global and project-level files."""
    config_data: dict = {}

    # Load global config first
    global_path = get_global_config_path()
    if global_path.exists():
        with open(global_path) as f:
            global_data = yaml.safe_load(f) or {}
            config_data.update(_resolve_env_vars_in_dict(global_data))

    # Override with project config
    project_path = get_project_config_path()
    if project_path.exists():
        with open(project_path) as f:
            project_data = yaml.safe_load(f) or {}
            # Deep merge for nested dicts
            resolved = _resolve_env_vars_in_dict(project_data)
            for key, value in resolved.items():
                if key in config_data and isinstance(config_data[key], dict) and isinstance(value, dict):
                    config_data[key].update(value)
                else:
                    config_data[key] = value

    # Also check environment variables directly
    if not config_data.get("api_keys"):
        config_data["api_keys"] = {}

    api_keys = config_data["api_keys"]
    if not api_keys.get("anthropic"):
        api_keys["anthropic"] = os.environ.get("ANTHROPIC_API_KEY")
    if not api_keys.get("openai"):
        api_keys["openai"] = os.environ.get("OPENAI_API_KEY")
    if not api_keys.get("google"):
        api_keys["google"] = os.environ.get("GOOGLE_API_KEY")

    return Config(**config_data)


def save_global_config(config: Config) -> None:
    """Save configuration to the global config file."""
    global_path = get_global_config_path()
    global_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(exclude_none=True)
    with open(global_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def save_project_config(config: Config) -> None:
    """Save configuration to the project-level config file."""
    project_path = get_project_config_path()

    data = config.model_dump(exclude_none=True)
    with open(project_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)
