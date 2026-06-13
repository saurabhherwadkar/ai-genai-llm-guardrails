"""
Core guardrail API routes.
Provides endpoints for validating input text, processing full LLM requests,
and retrieving guardrail configuration information.
"""

from fastapi import APIRouter, Depends  # Router and dependency injection.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.engine import GuardrailEngine  # Orchestration engine.
from guardrails.llm import create_llm_provider  # Provider factory function.
from guardrails.models.requests import GuardrailRequest  # Request body schema.
from guardrails.models.responses import GuardrailResponse  # Response body schema.

# Module-level logger instance for route handler events.
logger = get_logger(__name__)

# Create router instance for guardrail-related endpoints.
router = APIRouter(prefix="/api/v1/guardrails", tags=["Guardrails"])

# Module-level engine instance (lazy-initialized on first request).
_engine: GuardrailEngine | None = None


def _get_engine() -> GuardrailEngine:
    """Get or create the singleton guardrail engine instance.

    Lazily initializes the engine with configured LLM provider
    on first access for efficient resource usage.

    Returns:
        Configured GuardrailEngine instance ready for processing.
    """
    # Use module-level variable for singleton engine instance.
    global _engine
    # Create engine on first access with configured LLM provider.
    if _engine is None:
        # Create the LLM provider from application configuration.
        llm_provider = create_llm_provider()
        # Initialize the engine with the created provider.
        _engine = GuardrailEngine(llm_provider=llm_provider)
    # Return the singleton engine instance.
    return _engine


@router.post("/validate", response_model=GuardrailResponse)
async def validate_request(
    request: GuardrailRequest,
    engine: GuardrailEngine = Depends(_get_engine),  # noqa: B008
) -> GuardrailResponse:
    """Validate input text through the guardrail pipeline.

    Runs the input through all configured input guards, optionally
    processes with LLM, and validates output through output guards.

    Args:
        request: Validated request body with input text and options.
        engine: Injected guardrail engine instance.

    Returns:
        Complete GuardrailResponse with validation results and output.
    """
    # Log the incoming validation request with relevant metadata.
    logger.info(
        "validation_request_received",
        text_length=len(request.input_text),
        process_with_llm=request.process_with_llm,
    )
    # Process the request through the full guardrail engine pipeline.
    response = await engine.process_request(
        input_text=request.input_text,
        context=request.context,
        process_with_llm=request.process_with_llm,
        output_schema=request.output_schema,
    )
    # Log the completed validation result with outcome status.
    logger.info(
        "validation_request_completed",
        allowed=response.allowed,
        overall_action=response.overall_action,
    )
    # Return the complete guardrail response to the client.
    return response


@router.post("/validate/input", response_model=GuardrailResponse)
async def validate_input_only(
    request: GuardrailRequest,
    engine: GuardrailEngine = Depends(_get_engine),  # noqa: B008
) -> GuardrailResponse:
    """Validate input text through input guards only (no LLM processing).

    Runs only the input guardrail pipeline without LLM generation.
    Useful for pre-flight checks before submitting to an LLM.

    Args:
        request: Validated request body with input text to check.
        engine: Injected guardrail engine instance.

    Returns:
        GuardrailResponse with input validation results only.
    """
    # Log the input-only validation request.
    logger.info("input_validation_request_received", text_length=len(request.input_text))
    # Process without LLM regardless of request setting.
    response = await engine.process_request(
        input_text=request.input_text,
        context=request.context,
        process_with_llm=False,
    )
    # Return the input-only validation response.
    return response
