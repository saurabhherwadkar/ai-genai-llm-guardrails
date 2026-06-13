"""
Output validation guard.
Validates LLM output against structural constraints including
maximum length, format requirements, and optional JSON schema validation.
"""

import json  # JSON parsing for schema validation checks.
from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.

# Module-level logger instance for output validation events.
logger = get_logger(__name__)


class OutputValidatorGuard(BaseGuard):
    """Validates structural properties of LLM-generated output.

    Checks output length, emptiness, and optionally validates
    against a provided JSON schema when structured output is expected.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize output validator with validation constraints.

        Args:
            config: Guard settings including max length and schema enforcement.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load maximum allowed output length from configuration.
        self._max_output_length = config.get("max_output_length", 50000)
        # Load the action to take when validation fails.
        self._action = config.get("action", "block")
        # Load whether to enforce JSON schema validation when provided.
        self._enforce_schema = config.get("enforce_schema", True)

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Validate LLM output against structural and format constraints.

        Checks for empty output, excessive length, and JSON schema
        compliance if a schema is provided in the context.

        Args:
            text: LLM generated output text to validate structurally.
            context: Optional context containing output_schema for validation.

        Returns:
            GuardResult indicating whether output meets validation criteria.
        """
        # Log the start of output validation at debug level.
        logger.debug("output_validation_started", text_length=len(text))
        # Collect all validation failure reasons for reporting.
        violations: list[str] = []
        # Check if the LLM output is empty or contains only whitespace.
        if not text or not text.strip():
            # Empty output is a validation failure requiring action.
            violations.append("Output is empty or contains only whitespace")
        # Check if the output exceeds the maximum allowed length.
        elif len(text) > self._max_output_length:
            # Excessive length indicates potential runaway generation.
            violations.append(
                f"Output exceeds maximum length ({len(text)} > {self._max_output_length})"
            )
        # Validate against JSON schema if provided and enforcement enabled.
        if self._enforce_schema and context and context.get("output_schema"):
            # Attempt JSON schema validation of the output content.
            schema_result = self._validate_json_schema(text, context["output_schema"])
            # Add schema validation failure to violations if applicable.
            if schema_result:
                violations.append(schema_result)
        # Determine result based on whether any violations were found.
        if violations:
            # Log the validation failure with details for debugging.
            logger.warning(
                "output_validation_failed",
                violations=violations,
            )
            # Return blocking result with validation failure details.
            return GuardResult(
                guard_name=self.name,
                passed=False,
                action=self._action,
                severity=Severity.MEDIUM.value,
                message=f"Output validation failed: {'; '.join(violations)}",
                confidence=1.0,
                details={"violations": violations},
            )
        # Output passes all validation checks successfully.
        logger.debug("output_validation_passed", text_length=len(text))
        # Return passing result indicating output is structurally valid.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="Output passes all validation checks",
            confidence=0.0,
            details={},
        )

    @staticmethod
    def _validate_json_schema(text: str, schema: dict[str, Any]) -> str | None:
        """Validate output text against a JSON schema definition.

        Args:
            text: Output text expected to be valid JSON matching the schema.
            schema: JSON Schema definition to validate the output against.

        Returns:
            Error message string if validation fails, None if it passes.
        """
        # Attempt to parse the output text as JSON first.
        try:
            # Parse the text as JSON to check basic format validity.
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            # Return error message if output is not valid JSON format.
            return f"Output is not valid JSON: {e!s}"
        # Perform basic type checking against schema if type is specified.
        expected_type = schema.get("type")
        # Validate the parsed JSON matches the expected root type.
        if expected_type:
            # Map JSON Schema types to Python type checks.
            type_map = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "boolean": bool,
            }
            # Get the expected Python type for comparison.
            expected_python_type = type_map.get(expected_type)
            # Check if parsed output matches the expected type.
            if expected_python_type and not isinstance(parsed, expected_python_type):
                return (
                    f"Output type mismatch: expected {expected_type}, got {type(parsed).__name__}"
                )
        # Check for required properties if schema defines them.
        required_props = schema.get("required", [])
        # Validate all required properties are present in the output.
        if required_props and isinstance(parsed, dict):
            # Find any required properties missing from the parsed output.
            missing = [prop for prop in required_props if prop not in parsed]
            # Report missing required properties as a validation failure.
            if missing:
                return f"Missing required properties: {', '.join(missing)}"
        # Output passes JSON schema validation checks.
        return None
