"""
OpenAI LLM provider implementation.
Handles communication with the OpenAI API for chat completions.
Includes retry logic and proper error handling for production use.
"""

from typing import Any  # Generic type for flexible dictionary values.

import httpx  # Async HTTP client for API communication.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseLLMProvider  # Abstract provider interface.

# Module-level logger instance for OpenAI provider events.
logger = get_logger(__name__)

# OpenAI API endpoint for chat completions.
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider for generating LLM responses.

    Communicates with the OpenAI chat completions API using httpx.
    Supports configurable model, temperature, and retry settings.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize OpenAI provider with API credentials and settings.

        Args:
            config: Provider configuration including api_key and model settings.
        """
        # Call parent constructor to store provider configuration.
        super().__init__(config)
        # Load API key from configuration for authentication.
        self._api_key = config.get("api_key", "")
        # Load model identifier from configuration (default gpt-4o).
        self._model = config.get("model", "gpt-4o")
        # Load temperature setting for response randomness control.
        self._temperature = config.get("temperature", 0.7)
        # Load maximum tokens for response length control.
        self._max_tokens = config.get("max_tokens", 4096)
        # Load request timeout in seconds for API calls.
        self._timeout = config.get("timeout", 30)
        # Load maximum retry count for failed API calls.
        self._max_retries = config.get("max_retries", 3)
        # Log provider initialization with model identifier.
        logger.info("openai_provider_initialized", model=self._model)

    @property
    def provider_name(self) -> str:
        """Return the identifier string for the OpenAI provider.

        Returns:
            Provider name string identifying this as OpenAI.
        """
        # Return the static provider name for OpenAI implementation.
        return "openai"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from OpenAI's chat completions API.

        Makes an HTTP POST request to the OpenAI API with retry logic.

        Args:
            prompt: The user prompt text to send for completion.
            **kwargs: Additional parameters to override defaults.

        Returns:
            Generated text response from the OpenAI API.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        # Log the generation request with prompt length for monitoring.
        logger.debug("openai_generation_started", prompt_length=len(prompt))
        # Build the request payload for the chat completions API.
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }
        # Build authorization headers with the API key.
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Attempt the API call with retries on transient failures.
        last_error: Exception | None = None
        # Retry loop for handling transient API failures.
        for attempt in range(self._max_retries):
            try:
                # Create an async HTTP client with configured timeout.
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    # Send POST request to the OpenAI API endpoint.
                    response = await client.post(OPENAI_API_URL, json=payload, headers=headers)
                    # Raise exception for HTTP error status codes.
                    response.raise_for_status()
                    # Parse the JSON response body from the API.
                    data = response.json()
                    # Extract the generated text from the response structure.
                    generated_text = data["choices"][0]["message"]["content"]
                    # Log successful generation with response length.
                    logger.info(
                        "openai_generation_completed",
                        output_length=len(generated_text),
                    )
                    # Return the extracted generated text content.
                    return generated_text
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
                # Store the error for potential re-raise after all retries.
                last_error = e
                # Log the retry attempt with error details.
                logger.warning(
                    "openai_generation_retry",
                    attempt=attempt + 1,
                    error=str(e),
                )
        # All retry attempts exhausted — raise runtime error.
        error_msg = f"OpenAI API call failed after {self._max_retries} retries: {last_error}"
        # Log the final failure as an error event.
        logger.error("openai_generation_failed", error=error_msg)
        # Raise runtime error with the last recorded failure cause.
        raise RuntimeError(error_msg)

    async def health_check(self) -> bool:
        """Verify connectivity to the OpenAI API.

        Makes a minimal API call to verify authentication and reachability.

        Returns:
            True if the API key is valid and service is reachable.
        """
        # Skip health check if no API key is configured.
        if not self._api_key:
            logger.warning("openai_health_check_no_api_key")
            return False
        # Attempt a minimal request to verify API connectivity.
        try:
            # Create async client for the health check request.
            async with httpx.AsyncClient(timeout=10) as client:
                # Send minimal request to verify authentication.
                headers = {"Authorization": f"Bearer {self._api_key}"}
                # Check the models endpoint as a lightweight health probe.
                response = await client.get("https://api.openai.com/v1/models", headers=headers)
                # Return True if the API responds without auth errors.
                return response.status_code == 200
        except httpx.RequestError as e:
            # Log health check failure and return unhealthy status.
            logger.error("openai_health_check_failed", error=str(e))
            return False
