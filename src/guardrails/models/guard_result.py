"""
Guard result data transfer object.
Represents the outcome of a single guard evaluation with all relevant details.
Used by the pipeline to determine whether to proceed, warn, or halt processing.
"""

from pydantic import BaseModel, ConfigDict, Field  # Data validation and serialization.


class GuardResult(BaseModel):
    """Structured result from a single guard evaluation.

    Contains the guard's verdict, severity, and any relevant details
    about why the content was flagged or passed.
    """

    # Pydantic v2 model configuration for serialization and schema.
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "guard_name": "PIIDetector",
                "passed": False,
                "action": "block",
                "severity": "high",
                "message": "Email address detected in input",
                "confidence": 0.95,
                "details": {"pii_types": ["email"]},
                "modified_text": None,
            }
        }
    )

    # Name of the guard that produced this result.
    guard_name: str = Field(description="Identifier of the guard that ran")
    # Whether the content passed this guard's checks successfully.
    passed: bool = Field(description="True if content passed the guard check")
    # Recommended action: pass, warn, block, or redact.
    action: str = Field(default="pass", description="Recommended pipeline action")
    # Severity level if the guard detected an issue.
    severity: str = Field(default="low", description="Violation severity level")
    # Human-readable explanation of the guard's decision.
    message: str = Field(default="", description="Explanation of the evaluation result")
    # Confidence score of the detection between 0.0 and 1.0.
    confidence: float = Field(default=0.0, description="Detection confidence score")
    # Specific details about what was detected (e.g., PII types found).
    details: dict = Field(default_factory=dict, description="Additional detection details")
    # Modified text after redaction if applicable, None if unchanged.
    modified_text: str | None = Field(default=None, description="Redacted or sanitized text")
