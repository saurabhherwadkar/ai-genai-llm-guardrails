"""
Unit tests for the PII redactor output guard.
Validates that PII is properly redacted from LLM output text.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.guards.output.pii_redactor import PIIRedactorGuard  # Guard under test.


@pytest.fixture
def redactor_guard():
    """Create a PII redactor guard with default test configuration.

    Returns:
        Configured PIIRedactorGuard instance for testing.
    """
    # Create guard with standard redaction settings, longest patterns first.
    config = {
        "enabled": True,
        "redaction_char": "*",
        "min_redaction_length": 4,
        "redact_types": ["credit_card", "ssn", "email", "phone", "ip_address"],
    }
    # Return configured guard instance ready for evaluation testing.
    return PIIRedactorGuard(config)


@pytest.mark.asyncio
async def test_redacts_email_in_output(redactor_guard):
    """Verify emails are properly redacted from LLM output."""
    # Provide output containing an email address to redact.
    text = "You can reach support at admin@company.com for help."
    # Evaluate the text through the PII redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert the guard passes (redaction is not a block).
    assert result.passed is True
    # Assert the action is redact for modified content.
    assert result.action == "redact"
    # Assert the email is no longer visible in modified text.
    assert "admin@company.com" not in result.modified_text
    # Assert redaction characters replaced the email.
    assert "*" in result.modified_text


@pytest.mark.asyncio
async def test_redacts_phone_in_output(redactor_guard):
    """Verify phone numbers are properly redacted from LLM output."""
    # Provide output containing a phone number to redact.
    text = "Call our office at 555-123-4567 for more information."
    # Evaluate the text through the PII redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert the guard applied redaction action.
    assert result.action == "redact"
    # Assert the phone number is no longer visible in output.
    assert "555-123-4567" not in result.modified_text


@pytest.mark.asyncio
async def test_redacts_credit_card_in_output(redactor_guard):
    """Verify credit card numbers are properly redacted."""
    # Provide output containing a Visa credit card number to redact.
    text = "Card number is 4111111111111111 on file."
    # Evaluate the text through the PII redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert the card number is redacted from the output.
    assert "4111111111111111" not in result.modified_text
    # Assert credit_card is reported in redacted types.
    assert "credit_card" in result.details["redacted_types"]


@pytest.mark.asyncio
async def test_passes_clean_output(redactor_guard):
    """Verify output without PII passes unchanged."""
    # Provide output with no PII content present.
    text = "The capital of France is Paris, located in Europe."
    # Evaluate the clean text through the PII redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert the guard passes with no modifications needed.
    assert result.passed is True
    # Assert the action is pass (no redaction applied).
    assert result.action == "pass"
    # Assert modified text is None when no redaction occurred.
    assert result.modified_text is None


@pytest.mark.asyncio
async def test_redacts_multiple_pii_types(redactor_guard):
    """Verify multiple PII types are redacted in a single pass."""
    # Provide output with both email and phone PII to redact.
    text = "Contact user@test.com or call 555-987-6543 for support."
    # Evaluate the multi-PII text through the redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert multiple PII types were detected and redacted.
    assert len(result.details["redacted_types"]) >= 2
    # Assert neither PII value remains in the modified text.
    assert "user@test.com" not in result.modified_text
    assert "555-987-6543" not in result.modified_text


@pytest.mark.asyncio
async def test_preserves_non_pii_text(redactor_guard):
    """Verify non-PII text around redacted content is preserved."""
    # Provide output where PII is embedded in a longer sentence.
    text = "Hello, contact admin@example.com for details."
    # Evaluate the text through the PII redactor guard.
    result = await redactor_guard.evaluate(text)
    # Assert the non-PII parts of the sentence remain intact.
    assert "Hello, contact" in result.modified_text
    # Assert the trailing text is also preserved.
    assert "for details." in result.modified_text
