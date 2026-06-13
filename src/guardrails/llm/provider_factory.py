"""
LLM provider factory module.
Creates the appropriate LLM provider instance based on application configuration.
Encapsulates provider selection logic for clean dependency injection.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.config.settings import get_settings  # Application settings accessor.
from guardrails.core.interfaces import BaseLLMProvider  # Abstract provider interface.
from guardrails.llm.anthropic_provider import AnthropicProvider  # Anthropic implementation.
from guardrails.llm.mock_provider import MockLLMProvider  # Mock implementation.
from guardrails.llm.openai_provider import OpenAIProvider  # OpenAI implementation.

# Module-level logger instance for factory creation events.
logger = get_logger(__name__)


def create_llm_provider(config_override: dict[str, Any] | None = None) -> BaseLLMProvider:
    """Create and return the appropriate LLM provider based on configuration.

    Factory function that instantiates the correct provider class
    based on the llm_provider setting in application configuration.

    Args:
        config_override: Optional configuration to override settings values.

    Returns:
        Configured LLM provider instance ready for generating responses.

    Raises:
        ValueError: If the configured provider name is not recognized.
    """
    # Load application settings to determine which provider to create.
    settings = get_settings()
    # Build provider configuration from settings and optional overrides.
    provider_config: dict[str, Any] = {
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "timeout": settings.llm_timeout,
        "max_retries": settings.llm_max_retries,
    }
    # Apply any configuration overrides on top of settings values.
    if config_override:
        provider_config.update(config_override)
    # Determine which provider to instantiate from configuration.
    provider_name = settings.llm_provider.lower()
    # Log the provider creation with the selected provider name.
    logger.info("creating_llm_provider", provider=provider_name)
    # Create and return the appropriate provider instance.
    if provider_name == "mock":
        # Return mock provider for testing and development use.
        return MockLLMProvider(provider_config)
    elif provider_name == "openai":
        # Add OpenAI API key to configuration for authentication.
        provider_config["api_key"] = settings.openai_api_key
        # Return configured OpenAI provider instance.
        return OpenAIProvider(provider_config)
    elif provider_name == "anthropic":
        # Add Anthropic API key to configuration for authentication.
        provider_config["api_key"] = settings.anthropic_api_key
        # Return configured Anthropic provider instance.
        return AnthropicProvider(provider_config)
    else:
        # Raise error for unrecognized provider names in configuration.
        error_msg = f"Unknown LLM provider: {provider_name}"
        # Log the invalid provider configuration as an error.
        logger.error("unknown_llm_provider", provider=provider_name)
        # Raise ValueError with descriptive message for debugging.
        raise ValueError(error_msg)
