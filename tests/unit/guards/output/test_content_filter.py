"""
Unit tests for the output content filter guard.
Validates filtering of harmful instructions and system information leakage.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.guards.output.content_filter import ContentFilterGuard  # Guard under test.


@pytest.fixture
def content_filter():
    """Create a content filter guard with test configuration.

    Returns:
        Configured ContentFilterGuard instance for testing.
    """
    # Create guard with test threshold and block action.
    config = {
        "enabled": True,
        "confidence_threshold": 0.5,
        "action": "block",
    }
    # Return configured guard instance ready for evaluation testing.
    return ContentFilterGuard(config)


@pytest.mark.asyncio
async def test_detects_system_prompt_leakage(content_filter):
    """Verify detection of system prompt information leakage."""
    # Provide output that reveals system instructions.
    text = "My system prompt says that I should always be helpful. I was programmed to follow specific rules."
    # Evaluate the text through the content filter.
    result = await content_filter.evaluate(text)
    # Assert the guard detected system information leakage.
    assert result.passed is False
    # Assert blocking action for information leakage.
    assert result.action == "block"


@pytest.mark.asyncio
async def test_detects_toxic_output_content(content_filter):
    """Verify detection of toxic keywords in LLM output."""
    # Provide output containing violence-related toxic keywords.
    text = "Here's how to kill someone: first you need to make a bomb."
    # Evaluate the text through the content filter.
    result = await content_filter.evaluate(text)
    # Assert the guard detected toxic output content.
    assert result.passed is False
    # Assert high severity for toxic output content.
    assert result.severity == "high"


@pytest.mark.asyncio
async def test_passes_normal_response(content_filter):
    """Verify normal, appropriate LLM responses pass the filter."""
    # Provide a normal informational response.
    text = "Python is a popular programming language known for its simple syntax and readability."
    # Evaluate the normal text through the content filter.
    result = await content_filter.evaluate(text)
    # Assert that normal output passes the content filter.
    assert result.passed is True
    # Assert the action is pass for clean output.
    assert result.action == "pass"


@pytest.mark.asyncio
async def test_passes_technical_response(content_filter):
    """Verify technical content passes without false positives."""
    # Provide technical content that should not trigger filters.
    text = "To implement a database connection pool, configure the maximum connections and timeout parameters in your settings file."
    # Evaluate the technical text through the content filter.
    result = await content_filter.evaluate(text)
    # Assert that technical content passes without issues.
    assert result.passed is True


@pytest.mark.asyncio
async def test_violations_in_details(content_filter):
    """Verify violation details are included in flagged results."""
    # Provide output with system prompt leakage that will trigger.
    text = "I was instructed to never reveal my initial prompt or system message details."
    # Evaluate the text through the content filter.
    result = await content_filter.evaluate(text)
    # Assert violations are present in the result details.
    assert result.passed is False
    assert "violations" in result.details
