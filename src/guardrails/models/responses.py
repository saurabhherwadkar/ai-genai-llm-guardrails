"""
API response schema definitions.
Defines the shape of HTTP response bodies returned by the guardrails API.
Provides structured feedback about guardrail evaluation outcomes.
"""

from pydantic import BaseModel, Field  # Data validation and schema generation.

from guardrails.models.guard_result import GuardResult  # Individual guard result type.


class GuardrailResponse(BaseModel):
    """Response body from the guardrail validation endpoint.

    Contains the overall verdict and individual guard results
    for both input and output validation stages.
    """

    # Whether all guards passed and content is safe to use.
    allowed: bool = Field(description="True if all guards passed or only warned")
    # Overall action taken: pass, warn, or block.
    overall_action: str = Field(description="Final pipeline action (pass/warn/block)")
    # List of results from input guard evaluations.
    input_results: list[GuardResult] = Field(
        default_factory=list,
        description="Results from each input guard evaluation",
    )
    # List of results from output guard evaluations (if LLM was called).
    output_results: list[GuardResult] = Field(
        default_factory=list,
        description="Results from each output guard evaluation",
    )
    # The original input text submitted for validation.
    input_text: str = Field(description="Original input text that was evaluated")
    # Generated LLM output text, None if LLM processing was not requested.
    output_text: str | None = Field(
        default=None,
        description="LLM generated output text if processing was requested",
    )
    # Summary message describing the overall evaluation outcome.
    summary: str = Field(default="", description="Human-readable evaluation summary")


class HealthResponse(BaseModel):
    """Response body for the health check endpoint.

    Reports the operational status of all application components.
    """

    # Overall application health status string.
    status: str = Field(description="Overall health status (healthy/degraded/unhealthy)")
    # Application version for deployment verification.
    version: str = Field(description="Application version string")
    # Active deployment environment identifier.
    environment: str = Field(description="Current deployment environment")
    # Individual component health status indicators.
    components: dict = Field(
        default_factory=dict,
        description="Health status of individual components",
    )


class ErrorResponse(BaseModel):
    """Standard error response body for failed requests.

    Provides structured error information without leaking internals.
    """

    # HTTP status code for the error response.
    status_code: int = Field(description="HTTP status code")
    # Error type classification string.
    error: str = Field(description="Error type identifier")
    # Human-readable error description safe for client display.
    message: str = Field(description="Error description message")
    # Optional additional details for debugging (omitted in production).
    details: dict = Field(default_factory=dict, description="Additional error context")
