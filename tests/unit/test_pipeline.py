"""
Unit tests for the input and output pipeline modules.
Validates pipeline execution order, short-circuiting, and error handling.
"""

import pytest  # Test framework for assertions and fixtures.

from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard interface.
from guardrails.core.pipeline import InputPipeline, OutputPipeline  # Pipelines under test.
from guardrails.models.guard_result import GuardResult  # Result data structure.


class PassingGuard(BaseGuard):
    """Test guard that always passes evaluation."""

    async def evaluate(self, text, context=None):
        """Return a passing result for any input text."""
        # Always return a passing guard result for testing.
        return GuardResult(
            guard_name="PassingGuard",
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="Test pass",
        )


class BlockingGuard(BaseGuard):
    """Test guard that always blocks evaluation."""

    async def evaluate(self, text, context=None):
        """Return a blocking result for any input text."""
        # Always return a blocking guard result for testing.
        return GuardResult(
            guard_name="BlockingGuard",
            passed=False,
            action=GuardAction.BLOCK.value,
            severity=Severity.CRITICAL.value,
            message="Test block",
        )


class RedactingGuard(BaseGuard):
    """Test guard that redacts content in evaluation."""

    async def evaluate(self, text, context=None):
        """Return a redaction result with modified text."""
        # Return a redaction result replacing "secret" with asterisks.
        return GuardResult(
            guard_name="RedactingGuard",
            passed=True,
            action=GuardAction.REDACT.value,
            severity=Severity.MEDIUM.value,
            message="Test redaction",
            modified_text=text.replace("secret", "******"),
        )


class ErrorGuard(BaseGuard):
    """Test guard that raises an exception during evaluation."""

    async def evaluate(self, text, context=None):
        """Raise an exception to simulate guard failure."""
        # Raise an error to test pipeline error handling.
        raise RuntimeError("Simulated guard error")


@pytest.mark.asyncio
async def test_input_pipeline_all_pass():
    """Verify pipeline returns all passing results when no issues found."""
    # Create pipeline with multiple passing guards.
    pipeline = InputPipeline([PassingGuard({}), PassingGuard({})])
    # Execute the pipeline with clean input text.
    results = await pipeline.execute("clean text")
    # Assert both guards ran and returned results.
    assert len(results) == 2
    # Assert all results are passing.
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_input_pipeline_short_circuits_on_block():
    """Verify pipeline stops execution after a blocking guard."""
    # Create pipeline where blocking guard is second of three.
    pipeline = InputPipeline([PassingGuard({}), BlockingGuard({}), PassingGuard({})])
    # Execute the pipeline to trigger short-circuit.
    results = await pipeline.execute("test text")
    # Assert only two guards ran before short-circuit.
    assert len(results) == 2
    # Assert the last result is a block action.
    assert results[-1].action == GuardAction.BLOCK.value


@pytest.mark.asyncio
async def test_input_pipeline_skips_disabled_guards():
    """Verify pipeline skips guards that are disabled in config."""
    # Create a disabled passing guard by setting enabled to False.
    disabled_guard = PassingGuard({"enabled": False})
    # Create pipeline with one disabled and one enabled guard.
    pipeline = InputPipeline([disabled_guard, PassingGuard({})])
    # Execute the pipeline which should skip the disabled guard.
    results = await pipeline.execute("test text")
    # Assert only the enabled guard produced a result.
    assert len(results) == 1


@pytest.mark.asyncio
async def test_input_pipeline_handles_guard_error():
    """Verify pipeline handles exceptions from guards gracefully."""
    # Create pipeline with an error-throwing guard.
    pipeline = InputPipeline([ErrorGuard({})])
    # Execute the pipeline to trigger the error handler.
    results = await pipeline.execute("test text")
    # Assert a result was still produced for the errored guard.
    assert len(results) == 1
    # Assert the error result has block action for safety.
    assert results[0].action == GuardAction.BLOCK.value
    # Assert the guard did not pass.
    assert results[0].passed is False


@pytest.mark.asyncio
async def test_output_pipeline_applies_redaction():
    """Verify output pipeline applies text modifications from redaction guards."""
    # Create output pipeline with a redacting guard.
    pipeline = OutputPipeline([RedactingGuard({})])
    # Execute the pipeline with text containing the word "secret".
    results, modified_text = await pipeline.execute("this is a secret value")
    # Assert the redacting guard produced a result.
    assert len(results) == 1
    # Assert the word "secret" was replaced in the output.
    assert "secret" not in modified_text
    # Assert the redaction characters are present.
    assert "******" in modified_text


@pytest.mark.asyncio
async def test_output_pipeline_chains_modifications():
    """Verify output pipeline chains text modifications from multiple guards."""
    # Create output pipeline with two redacting guards.
    pipeline = OutputPipeline([RedactingGuard({}), PassingGuard({})])
    # Execute with text that the redacting guard will modify.
    results, modified_text = await pipeline.execute("my secret data")
    # Assert both guards ran and produced results.
    assert len(results) == 2
    # Assert the redaction was applied to the final text.
    assert "secret" not in modified_text


@pytest.mark.asyncio
async def test_output_pipeline_short_circuits_on_block():
    """Verify output pipeline stops after a blocking guard."""
    # Create pipeline where blocking guard prevents further processing.
    pipeline = OutputPipeline([BlockingGuard({}), RedactingGuard({})])
    # Execute the pipeline to trigger short-circuit.
    results, modified_text = await pipeline.execute("test secret text")
    # Assert only one guard ran before the block.
    assert len(results) == 1
    # Assert the result is a block action.
    assert results[0].action == GuardAction.BLOCK.value
