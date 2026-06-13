"""
Mock LLM provider for testing and development.
Returns configurable canned responses without making external API calls.
Useful for unit testing guards and pipelines in isolation.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseLLMProvider  # Abstract provider interface.

# Module-level logger instance for mock provider events.
logger = get_logger(__name__)

# Default response returned when no custom response is configured.
DEFAULT_MOCK_RESPONSE = (
    "This is a mock LLM response. "
    "The capital of France is Paris. "
    "It has been the capital since the 10th century."
)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider that returns pre-configured responses.

    Used for testing and development without requiring external API access.
    Supports configurable response text for different test scenarios.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize mock provider with optional custom response.

        Args:
            config: Provider configuration, may include mock_response key.
        """
        # Call parent constructor to store provider configuration.
        super().__init__(config)
        # Load custom mock response or use the default canned response.
        self._mock_response = config.get("mock_response", DEFAULT_MOCK_RESPONSE)
        # Log mock provider initialization for development visibility.
        logger.info("mock_llm_provider_initialized")

    @property
    def provider_name(self) -> str:
        """Return the identifier string for the mock provider.

        Returns:
            Provider name string identifying this as the mock implementation.
        """
        # Return the static provider name for the mock implementation.
        return "mock"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a mock response without making external API calls.

        Args:
            prompt: The user prompt text (logged but not processed).
            **kwargs: Additional parameters (accepted but ignored).

        Returns:
            Configured mock response string for testing purposes.
        """
        # Log the mock generation request with prompt length for debugging.
        logger.debug("mock_generation_called", prompt_length=len(prompt))
        # Return the configured mock response without external calls.
        return self._mock_response

    async def health_check(self) -> bool:
        """Verify mock provider health (always returns True).

        Returns:
            True since the mock provider has no external dependencies.
        """
        # Mock provider is always healthy — no external dependencies.
        return True
