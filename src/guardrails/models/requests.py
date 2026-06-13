"""
API request schema definitions.
Defines the shape of incoming HTTP request bodies for the guardrails API.
Uses Pydantic for automatic validation and OpenAPI documentation generation.
"""

from pydantic import BaseModel, ConfigDict, Field  # Data validation and schema generation.


class GuardrailRequest(BaseModel):
    """Request body for the guardrail validation endpoint.

    Contains the text to validate and optional context for evaluation.
    """

    # Pydantic v2 model configuration with example payload for docs.
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input_text": "What is the capital of France?",
                "context": {"user_id": "user-123", "session_id": "sess-456"},
                "process_with_llm": True,
                "output_schema": None,
            }
        }
    )

    # The input text (prompt) to run through input guardrails.
    input_text: str = Field(
        description="Text content to validate through input guardrails",
        min_length=1,
        max_length=50000,
    )
    # Optional context about the request source or intent.
    context: dict = Field(
        default_factory=dict,
        description="Additional context for guard evaluation decisions",
    )
    # Whether to also run the text through LLM and validate output.
    process_with_llm: bool = Field(
        default=False,
        description="If true, send validated input to LLM and validate output",
    )
    # Optional JSON schema to validate structured LLM output against.
    output_schema: dict | None = Field(
        default=None,
        description="JSON schema for validating structured LLM output",
    )


class HealthCheckRequest(BaseModel):
    """Request body for detailed health check endpoint.

    Allows specifying which components to check health for.
    """

    # Whether to include LLM provider health in the check.
    include_llm: bool = Field(
        default=False,
        description="Include LLM provider connectivity check",
    )
