"""
Anthropic LLM provider implementation.
Handles communication with the Anthropic Messages API for Claude models.
Includes retry logic and proper error handling for production use.
"""

from typing import Any  # Generic type for flexible dictionary values.

import httpx  # Async HTTP client for API communication.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseLLMProvider  # Abstract provider interface.

# Module-level logger instance for Anthropic provider events.
logger = get_logger(__name__)

# Anthropic API endpoint for messages.
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Current Anthropic API version header value.
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider for generating LLM responses via Claude.

    Communicates with the Anthropic Messages API using httpx.
    Supports configurable model, temperature, and retry settings.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Anthropic provider with API credentials and settings.

        Args:
            config: Provider configuration including api_key and model settings.
        """
        # Call parent constructor to store provider configuration.
        super().__init__(config)
        # Load API key from configuration for authentication.
        self._api_key = config.get("api_key", "")
        # Load model identifier (default claude-sonnet-4-20250514).
        self._model = config.get("model", "claude-sonnet-4-20250514")
        # Load temperature setting for response randomness control.
        self._temperature = config.get("temperature", 0.7)
        # Load maximum tokens for response length control.
        self._max_tokens = config.get("max_tokens", 4096)
        # Load request timeout in seconds for API calls.
        self._timeout = config.get("timeout", 30)
        # Load maximum retry count for failed API calls.
        self._max_retries = config.get("max_retries", 3)
        # Log provider initialization with model identifier.
        logger.info("anthropic_provider_initialized", model=self._model)

    @property
    def provider_name(self) -> str:
        """Return the identifier string for the Anthropic provider.

        Returns:
            Provider name string identifying this as Anthropic.
        """
        # Return the static provider name for Anthropic implementation.
        return "anthropic"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from Anthropic's Messages API.

        Makes an HTTP POST request to the Anthropic API with retry logic.

        Args:
            prompt: The user prompt text to send for completion.
            **kwargs: Additional parameters to override defaults.

        Returns:
            Generated text response from the Anthropic API.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        # Log the generation request with prompt length for monitoring.
        logger.debug("anthropic_generation_started", prompt_length=len(prompt))
        # Build the request payload for the Messages API.
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }
        # Build authorization headers with API key and version.
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        }
        # Attempt the API call with retries on transient failures.
        last_error: Exception | None = None
        # Retry loop for handling transient API failures.
        for attempt in range(self._max_retries):
            try:
                # Create an async HTTP client with configured timeout.
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    # Send POST request to the Anthropic API endpoint.
                    response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
                    # Raise exception for HTTP error status codes.
                    response.raise_for_status()
                    # Parse the JSON response body from the API.
                    data = response.json()
                    # Extract the generated text from the response structure.
                    generated_text = data["content"][0]["text"]
                    # Log successful generation with response length.
                    logger.info(
                        "anthropic_generation_completed",
                        output_length=len(generated_text),
                    )
                    # Return the extracted generated text content.
                    return generated_text
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
                # Store the error for potential re-raise after all retries.
                last_error = e
                # Log the retry attempt with error details.
                logger.warning(
                    "anthropic_generation_retry",
                    attempt=attempt + 1,
                    error=str(e),
                )
        # All retry attempts exhausted — raise runtime error.
        error_msg = f"Anthropic API call failed after {self._max_retries} retries: {last_error}"
        # Log the final failure as an error event.
        logger.error("anthropic_generation_failed", error=error_msg)
        # Raise runtime error with the last recorded failure cause.
        raise RuntimeError(error_msg)

    async def health_check(self) -> bool:
        """Verify connectivity to the Anthropic API.

        Makes a minimal API call to verify authentication and reachability.

        Returns:
            True if the API key is valid and service is reachable.
        """
        # Skip health check if no API key is configured.
        if not self._api_key:
            logger.warning("anthropic_health_check_no_api_key")
            return False
        # Attempt a minimal request to verify API connectivity.
        try:
            # Create async client for the health check request.
            async with httpx.AsyncClient(timeout=10) as client:
                # Build minimal payload to test authentication.
                payload = {
                    "model": self._model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }
                # Build headers with API key for authentication check.
                headers = {
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "Content-Type": "application/json",
                }
                # Send minimal request to verify the API responds.
                response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
                # Return True if API accepts the request (200 or 201).
                return response.status_code in (200, 201)
        except httpx.RequestError as e:
            # Log health check failure and return unhealthy status.
            logger.error("anthropic_health_check_failed", error=str(e))
            return False
