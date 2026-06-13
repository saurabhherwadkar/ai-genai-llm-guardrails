"""
Application settings module.
Loads configuration from YAML files with environment-specific overlays.
Uses pydantic-settings for type-safe configuration management.
"""

import os  # Standard library import for environment variable access.
from functools import lru_cache  # Caching decorator for singleton settings.
from pathlib import Path  # Object-oriented filesystem path handling.
from typing import Any  # Type hint for generic dictionary values.

import yaml  # YAML parser for configuration file loading.
from pydantic import Field  # Field descriptor for pydantic models.
from pydantic_settings import BaseSettings, SettingsConfigDict  # Settings base and config.

# Resolve the project root directory relative to this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Path to the configuration directory containing YAML files.
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load a single YAML file and return its contents as a dictionary.

    Args:
        file_path: Absolute path to the YAML configuration file.

    Returns:
        Dictionary of configuration values, empty dict if file missing.
    """
    # Return empty dict if the configuration file does not exist.
    if not file_path.exists():
        return {}
    # Open and parse the YAML file safely.
    with open(file_path, encoding="utf-8") as f:
        # Use safe_load to prevent arbitrary code execution from YAML.
        content = yaml.safe_load(f)
    # Return empty dict if file is empty or contains only comments.
    return content if content else {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dictionary into base dictionary.

    Args:
        base: The base configuration dictionary.
        override: The environment-specific override dictionary.

    Returns:
        Merged dictionary with override values taking precedence.
    """
    # Create a copy to avoid mutating the original base dictionary.
    merged = base.copy()
    # Iterate through each key-value pair in the override dictionary.
    for key, value in override.items():
        # Recursively merge nested dictionaries for deep configuration.
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            # Override scalar values directly from environment config.
            merged[key] = value
    # Return the fully merged configuration dictionary.
    return merged


def load_config() -> dict[str, Any]:
    """Load and merge application configuration from YAML files.

    Loads base config then applies environment-specific overlay.
    Environment is determined by APP_ENV environment variable.

    Returns:
        Fully merged configuration dictionary ready for settings parsing.
    """
    # Load the base application configuration shared across environments.
    base_config = _load_yaml_file(CONFIG_DIR / "application.yaml")
    # Determine the active environment from APP_ENV variable, default to dev.
    env = os.getenv("APP_ENV", "dev")
    # Load environment-specific overrides (e.g., application-dev.yaml).
    env_config = _load_yaml_file(CONFIG_DIR / f"application-{env}.yaml")
    # Merge environment overrides on top of base configuration.
    merged = _deep_merge(base_config, env_config)
    # Return the final merged configuration dictionary.
    return merged


def load_guardrails_config() -> dict[str, Any]:
    """Load guardrail-specific configuration from guardrails.yaml.

    Returns:
        Dictionary containing all guard toggles and threshold settings.
    """
    # Load the guardrails configuration file with guard-specific settings.
    return _load_yaml_file(CONFIG_DIR / "guardrails.yaml")


class AppSettings(BaseSettings):
    """Application-level settings with type validation.

    Attributes define the core application configuration parameters.
    Values are loaded from YAML config merged with environment variables.
    """

    # Human-readable application name for logging and health checks.
    app_name: str = Field(default="ai-genai-llm-guardrails")
    # Semantic version string for API versioning and health endpoints.
    app_version: str = Field(default="1.0.0")
    # Enable debug mode for verbose logging and error details.
    debug: bool = Field(default=False)
    # Network interface address the server binds to.
    server_host: str = Field(default="0.0.0.0")  # noqa: S104
    # TCP port number for the HTTP server listener.
    server_port: int = Field(default=8000)
    # Number of worker processes for handling concurrent requests.
    server_workers: int = Field(default=4)
    # Minimum log severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_level: str = Field(default="INFO")
    # Log output format: "json" for structured, "console" for readable.
    log_format: str = Field(default="json")
    # Active LLM provider identifier (mock, openai, anthropic).
    llm_provider: str = Field(default="mock")
    # Maximum seconds to wait for LLM provider API response.
    llm_timeout: int = Field(default=30)
    # Number of retry attempts for failed LLM API calls.
    llm_max_retries: int = Field(default=3)
    # Sampling temperature for LLM response generation randomness.
    llm_temperature: float = Field(default=0.7)
    # Maximum token count for LLM response generation.
    llm_max_tokens: int = Field(default=4096)
    # OpenAI API key for authenticating with OpenAI services.
    openai_api_key: str = Field(default="")
    # Anthropic API key for authenticating with Anthropic services.
    anthropic_api_key: str = Field(default="")
    # Active deployment environment identifier (dev, staging, prod).
    app_env: str = Field(default="dev")

    # Pydantic v2 settings configuration for environment variable loading.
    model_config = SettingsConfigDict(
        # No prefix for environment variable names.
        env_prefix="",
        # Load values from .env file in project root.
        env_file=".env",
        # Allow extra fields from config without raising validation errors.
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Create and cache the application settings singleton.

    Loads from YAML config files, then overlays environment variables.
    Cached so repeated calls return the same instance efficiently.

    Returns:
        Validated AppSettings instance with all configuration loaded.
    """
    # Load merged YAML configuration from base and environment files.
    config = load_config()
    # Extract nested configuration sections with safe defaults.
    app_config = config.get("app", {})
    server_config = config.get("server", {})
    logging_config = config.get("logging", {})
    llm_config = config.get("llm", {})
    # Build flat settings dictionary from nested YAML structure.
    settings_dict = {
        "app_name": app_config.get("name", "ai-genai-llm-guardrails"),
        "app_version": app_config.get("version", "1.0.0"),
        "debug": app_config.get("debug", False),
        "server_host": server_config.get("host", "0.0.0.0"),  # noqa: S104
        "server_port": server_config.get("port", 8000),
        "server_workers": server_config.get("workers", 4),
        "log_level": logging_config.get("level", "INFO"),
        "log_format": logging_config.get("format", "json"),
        "llm_provider": llm_config.get("provider", "mock"),
        "llm_timeout": llm_config.get("timeout_seconds", 30),
        "llm_max_retries": llm_config.get("max_retries", 3),
        "llm_temperature": llm_config.get("temperature", 0.7),
        "llm_max_tokens": llm_config.get("max_tokens", 4096),
        "app_env": os.getenv("APP_ENV", "dev"),
    }
    # Create settings with YAML values as defaults, env vars take precedence.
    return AppSettings(**settings_dict)
