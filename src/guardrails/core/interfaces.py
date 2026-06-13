"""
Abstract base classes defining the guard and LLM provider contracts.
All concrete guards and providers must implement these interfaces.
This ensures consistent behavior and enables polymorphic pipeline execution.
"""

from abc import ABC, abstractmethod  # Abstract base class machinery.
from enum import StrEnum  # String enumeration for fixed value sets.
from typing import Any  # Generic type hint for flexible dictionary values.

from guardrails.models.guard_result import GuardResult  # Result data transfer object.


class Severity(StrEnum):
    """Severity levels for guardrail violations.

    Determines how the pipeline responds to a guard failure.
    """

    # Low severity: informational, does not block processing.
    LOW = "low"
    # Medium severity: warning-level, may require attention.
    MEDIUM = "medium"
    # High severity: significant risk, should be reviewed.
    HIGH = "high"
    # Critical severity: immediate block, processing halts.
    CRITICAL = "critical"


class GuardAction(StrEnum):
    """Actions a guard can recommend after evaluation.

    Controls the pipeline's response to a guard result.
    """

    # Allow the content to pass through without modification.
    PASS = "pass"  # noqa: S105
    # Warn about potential issues but allow content to proceed.
    WARN = "warn"
    # Block the content from further processing in the pipeline.
    BLOCK = "block"
    # Modify the content by redacting or sanitizing problematic parts.
    REDACT = "redact"


class BaseGuard(ABC):
    """Abstract base class for all guardrail implementations.

    Each guard evaluates text content and returns a structured result
    indicating whether the content passes, should be warned about,
    or must be blocked from further processing.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the guard with its configuration dictionary.

        Args:
            config: Guard-specific settings from guardrails.yaml.
        """
        # Store the guard configuration for use during evaluation.
        self._config = config
        # Determine if this guard is enabled from configuration.
        self._enabled = config.get("enabled", True)

    @property
    def name(self) -> str:
        """Return the human-readable name of this guard.

        Returns:
            String identifier for this guard, used in logging and results.
        """
        # Default implementation uses the class name as the guard name.
        return self.__class__.__name__

    @property
    def enabled(self) -> bool:
        """Check if this guard is currently enabled.

        Returns:
            True if the guard should run, False to skip it.
        """
        # Return the enabled state loaded from configuration.
        return self._enabled

    @abstractmethod
    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate the given text against this guard's rules.

        Args:
            text: The text content to evaluate (input prompt or LLM output).
            context: Optional additional context for evaluation decisions.

        Returns:
            GuardResult indicating pass/warn/block with details.
        """
        ...  # Concrete implementations must override this method.


class BaseLLMProvider(ABC):
    """Abstract base class for LLM provider integrations.

    Defines the contract that all LLM providers must implement
    for generating responses from prompts.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the LLM provider with connection configuration.

        Args:
            config: Provider-specific settings (API keys, timeouts, etc).
        """
        # Store provider configuration for use during API calls.
        self._config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the identifier string for this LLM provider.

        Returns:
            Provider name string (e.g., "openai", "anthropic", "mock").
        """
        ...  # Each provider must declare its own name.

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the LLM for the given prompt.

        Args:
            prompt: The user prompt text to send to the LLM.
            **kwargs: Additional provider-specific generation parameters.

        Returns:
            Generated text response from the LLM provider.

        Raises:
            LLMProviderError: If the API call fails after retries.
        """
        ...  # Concrete providers implement their specific API calls.

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity to the LLM provider service.

        Returns:
            True if the provider is reachable and authenticated.
        """
        ...  # Each provider validates its own connection health.
