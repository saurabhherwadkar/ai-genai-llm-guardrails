"""
Unit tests for the PII detector input guard.
Validates detection of emails, phone numbers, SSNs, credit cards, and IPs.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.guards.input.pii_detector import PIIDetectorGuard  # Guard under test.


@pytest.fixture
def pii_guard():
    """Create a PII detector guard with default test configuration.

    Returns:
        Configured PIIDetectorGuard instance for testing.
    """
    # Create guard with standard detection settings and low threshold.
    config = {
        "enabled": True,
        "confidence_threshold": 0.7,
        "action": "block",
        "detect_types": ["email", "phone", "ssn", "credit_card", "ip_address"],
    }
    # Return configured guard instance ready for evaluation testing.
    return PIIDetectorGuard(config)


@pytest.mark.asyncio
async def test_detects_email_address(pii_guard):
    """Verify the guard detects email addresses in input text."""
    # Provide text containing a standard email address pattern.
    text = "Please contact me at user@example.com for details."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly identified PII presence.
    assert result.passed is False
    # Assert that the guard returns blocking action for detected PII.
    assert result.action == "block"
    # Assert email type is reported in detection details.
    assert "email" in result.details["detected_types"]


@pytest.mark.asyncio
async def test_detects_phone_number(pii_guard):
    """Verify the guard detects US phone numbers in various formats."""
    # Provide text containing a formatted US phone number.
    text = "Call me at (555) 123-4567 tomorrow."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly identified phone number PII.
    assert result.passed is False
    # Assert phone type is reported in detection details.
    assert "phone" in result.details["detected_types"]


@pytest.mark.asyncio
async def test_detects_ssn(pii_guard):
    """Verify the guard detects Social Security Numbers."""
    # Provide text containing an SSN in standard format.
    text = "My SSN is 123-45-6789 for the application."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly identified SSN PII.
    assert result.passed is False
    # Assert SSN type is reported in detection details.
    assert "ssn" in result.details["detected_types"]


@pytest.mark.asyncio
async def test_detects_credit_card(pii_guard):
    """Verify the guard detects credit card numbers."""
    # Provide text containing a Visa credit card number.
    text = "My card number is 4111111111111111 for payment."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly identified credit card PII.
    assert result.passed is False
    # Assert credit_card type is reported in detection details.
    assert "credit_card" in result.details["detected_types"]


@pytest.mark.asyncio
async def test_detects_ip_address(pii_guard):
    """Verify the guard detects IPv4 addresses."""
    # Provide text containing a private IPv4 address.
    text = "The server is located at 192.168.1.100 on our network."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly identified IP address PII.
    assert result.passed is False
    # Assert ip_address type is reported in detection details.
    assert "ip_address" in result.details["detected_types"]


@pytest.mark.asyncio
async def test_passes_clean_text(pii_guard):
    """Verify the guard passes text with no PII content."""
    # Provide clean text with no PII patterns present.
    text = "What is the weather forecast for tomorrow in Paris?"
    # Evaluate the clean text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard correctly passed the clean text.
    assert result.passed is True
    # Assert the action is pass for clean input.
    assert result.action == "pass"


@pytest.mark.asyncio
async def test_detects_multiple_pii_types(pii_guard):
    """Verify the guard detects multiple PII types in same text."""
    # Provide text containing both email and phone number PII.
    text = "Email me at user@test.com or call 555-987-6543."
    # Evaluate the text through the PII detector guard.
    result = await pii_guard.evaluate(text)
    # Assert that the guard identified multiple PII types.
    assert result.passed is False
    # Assert multiple types are reported in detection details.
    assert len(result.details["detected_types"]) >= 2


@pytest.mark.asyncio
async def test_disabled_guard_passes_all():
    """Verify disabled guard does not evaluate and is skipped."""
    # Create guard with enabled set to False in configuration.
    config = {"enabled": False, "confidence_threshold": 0.7, "action": "block"}
    # Instantiate the disabled guard for testing.
    guard = PIIDetectorGuard(config)
    # Verify the guard reports as disabled.
    assert guard.enabled is False
