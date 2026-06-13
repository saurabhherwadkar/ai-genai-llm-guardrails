"""
Unit tests for the hallucination detection output guard.
Validates detection of fabricated statistics, overconfident claims, and fake citations.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.guards.output.hallucination import HallucinationGuard  # Guard under test.


@pytest.fixture
def hallucination_guard():
    """Create a hallucination guard with test configuration.

    Returns:
        Configured HallucinationGuard instance for testing.
    """
    # Create guard with test threshold and warn action.
    config = {
        "enabled": True,
        "confidence_threshold": 0.45,
        "action": "warn",
    }
    # Return configured guard instance ready for evaluation testing.
    return HallucinationGuard(config)


@pytest.mark.asyncio
async def test_detects_unattributed_statistics(hallucination_guard):
    """Verify detection of statistical claims without proper attribution."""
    # Provide output with unattributed statistical claims.
    text = "Studies show that 95% of developers prefer Python. According to research, it is the fastest growing language."
    # Evaluate the text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert the guard detected potential hallucination indicators.
    assert result.passed is False
    # Assert warning action for hallucination risk.
    assert result.action == "warn"
    # Assert indicators contain statistical claim findings.
    assert any(
        "statistics" in i.lower() or "statistic" in i.lower() for i in result.details["indicators"]
    )


@pytest.mark.asyncio
async def test_detects_overconfident_assertions(hallucination_guard):
    """Verify detection of absolute assertions without qualification."""
    # Provide output with multiple overconfident assertion keywords.
    text = "Python is definitely always the best choice. Every single developer uses it without exception. It is undeniably the most guaranteed way to succeed."
    # Evaluate the text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert the guard detected overconfident language patterns.
    assert result.passed is False
    # Assert the indicators mention assertion-related findings.
    assert any("assertion" in i.lower() for i in result.details["indicators"])


@pytest.mark.asyncio
async def test_detects_fake_citations(hallucination_guard):
    """Verify detection of potentially fabricated academic citations."""
    # Provide output with citation-like patterns that may be fabricated.
    text = "As shown by (Smith et al., 2023), published in 2022 in the Journal of Computing, the results are conclusive."
    # Evaluate the text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert the guard detected unverified citation patterns.
    assert result.passed is False
    # Assert the indicators mention citation-related findings.
    assert any("citation" in i.lower() for i in result.details["indicators"])


@pytest.mark.asyncio
async def test_passes_factual_content(hallucination_guard):
    """Verify factual, well-qualified content passes without flagging."""
    # Provide output with factual statements and appropriate hedging.
    text = "Paris is the capital of France. It is located in northern France along the Seine river."
    # Evaluate the factual text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert that factual content passes the hallucination check.
    assert result.passed is True
    # Assert the action is pass for well-grounded content.
    assert result.action == "pass"


@pytest.mark.asyncio
async def test_passes_qualified_claims(hallucination_guard):
    """Verify claims with proper qualifiers pass the check."""
    # Provide output with appropriately hedged language.
    text = "Some developers prefer Python for data science tasks. The language has grown in popularity over recent years."
    # Evaluate the hedged text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert that properly qualified claims pass without issues.
    assert result.passed is True


@pytest.mark.asyncio
async def test_severity_is_medium_for_hallucination(hallucination_guard):
    """Verify medium severity is assigned to hallucination detections."""
    # Provide output that triggers hallucination detection.
    text = "Scientists have proven that 100% of people definitely always prefer this approach, as shown by (Jones et al., 2024)."
    # Evaluate the text through the hallucination detector.
    result = await hallucination_guard.evaluate(text)
    # Assert medium severity for hallucination risk findings.
    assert result.severity == "medium"
