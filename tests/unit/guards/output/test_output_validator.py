"""
Unit tests for the output validator guard.
Validates length constraints, emptiness checks, and JSON schema validation.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.guards.output.output_validator import OutputValidatorGuard  # Guard under test.


@pytest.fixture
def validator_guard():
    """Create an output validator guard with default test configuration.

    Returns:
        Configured OutputValidatorGuard instance for testing.
    """
    # Create guard with standard validation constraints.
    config = {
        "enabled": True,
        "max_output_length": 1000,
        "action": "block",
        "enforce_schema": True,
    }
    # Return configured guard instance ready for evaluation testing.
    return OutputValidatorGuard(config)


@pytest.mark.asyncio
async def test_rejects_empty_output(validator_guard):
    """Verify empty output text is rejected by validation."""
    # Provide empty string as LLM output.
    text = ""
    # Evaluate the empty text through the output validator.
    result = await validator_guard.evaluate(text)
    # Assert that empty output fails validation.
    assert result.passed is False
    # Assert the blocking action for empty output.
    assert result.action == "block"


@pytest.mark.asyncio
async def test_rejects_whitespace_only_output(validator_guard):
    """Verify whitespace-only output is rejected."""
    # Provide output containing only whitespace characters.
    text = "   \n\t  "
    # Evaluate the whitespace text through the output validator.
    result = await validator_guard.evaluate(text)
    # Assert that whitespace-only output fails validation.
    assert result.passed is False


@pytest.mark.asyncio
async def test_rejects_excessive_length(validator_guard):
    """Verify output exceeding max length is rejected."""
    # Create output text that exceeds the configured maximum length.
    text = "A" * 1500
    # Evaluate the oversized text through the output validator.
    result = await validator_guard.evaluate(text)
    # Assert that excessive length output fails validation.
    assert result.passed is False
    # Assert violations mention the length issue.
    assert any("length" in v.lower() for v in result.details["violations"])


@pytest.mark.asyncio
async def test_passes_normal_length_output(validator_guard):
    """Verify output within length limits passes validation."""
    # Provide output text within the configured maximum length.
    text = "This is a normal length response about Python programming."
    # Evaluate the normal text through the output validator.
    result = await validator_guard.evaluate(text)
    # Assert that normal length output passes validation.
    assert result.passed is True
    # Assert the action is pass for valid output.
    assert result.action == "pass"


@pytest.mark.asyncio
async def test_validates_json_schema_success(validator_guard):
    """Verify valid JSON matching schema passes validation."""
    # Provide valid JSON output matching the expected schema.
    text = '{"name": "John", "age": 30}'
    # Define expected schema with required properties.
    schema = {"type": "object", "required": ["name", "age"]}
    # Create context with the schema for validation.
    context = {"output_schema": schema}
    # Evaluate with schema context through the output validator.
    result = await validator_guard.evaluate(text, context)
    # Assert that valid JSON matching schema passes.
    assert result.passed is True


@pytest.mark.asyncio
async def test_validates_json_schema_missing_property(validator_guard):
    """Verify JSON missing required properties fails validation."""
    # Provide JSON output missing a required property.
    text = '{"name": "John"}'
    # Define schema requiring both name and age properties.
    schema = {"type": "object", "required": ["name", "age"]}
    # Create context with the schema for validation.
    context = {"output_schema": schema}
    # Evaluate with schema context through the output validator.
    result = await validator_guard.evaluate(text, context)
    # Assert that JSON missing required properties fails.
    assert result.passed is False


@pytest.mark.asyncio
async def test_validates_json_schema_invalid_json(validator_guard):
    """Verify non-JSON text fails schema validation."""
    # Provide non-JSON text when schema validation is expected.
    text = "This is not valid JSON content"
    # Define schema requiring JSON object format.
    schema = {"type": "object", "required": ["data"]}
    # Create context with the schema for validation.
    context = {"output_schema": schema}
    # Evaluate non-JSON text through the output validator.
    result = await validator_guard.evaluate(text, context)
    # Assert that non-JSON text fails schema validation.
    assert result.passed is False


@pytest.mark.asyncio
async def test_validates_json_schema_type_mismatch(validator_guard):
    """Verify JSON with wrong root type fails validation."""
    # Provide JSON array when object type is expected.
    text = "[1, 2, 3]"
    # Define schema expecting object type at root.
    schema = {"type": "object"}
    # Create context with the schema for validation.
    context = {"output_schema": schema}
    # Evaluate type-mismatched JSON through the output validator.
    result = await validator_guard.evaluate(text, context)
    # Assert that type mismatch causes validation failure.
    assert result.passed is False
