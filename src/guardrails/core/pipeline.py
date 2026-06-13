"""
Guardrail pipeline module.
Provides input and output pipeline classes that chain guards sequentially.
Pipelines evaluate text through all enabled guards and aggregate results.
Short-circuits on BLOCK action to prevent unnecessary processing.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction  # Guard interface and actions.
from guardrails.models.guard_result import GuardResult  # Individual guard result type.

# Module-level logger instance for pipeline execution events.
logger = get_logger(__name__)


class InputPipeline:
    """Pipeline that runs input guards sequentially on user prompts.

    Guards execute in order. Pipeline short-circuits if any guard
    returns a BLOCK action, skipping remaining guards for efficiency.
    """

    def __init__(self, guards: list[BaseGuard]) -> None:
        """Initialize input pipeline with an ordered list of guards.

        Args:
            guards: Ordered list of input guard instances to execute.
        """
        # Store the ordered guard list for sequential execution.
        self._guards = guards
        # Log the pipeline initialization with guard count.
        logger.info("input_pipeline_initialized", guard_count=len(guards))

    async def execute(self, text: str, context: dict[str, Any] | None = None) -> list[GuardResult]:
        """Execute all enabled input guards on the provided text.

        Runs guards sequentially, short-circuiting on BLOCK action.
        Skips disabled guards without evaluation.

        Args:
            text: User input text to evaluate through the guard chain.
            context: Optional context dictionary passed to each guard.

        Returns:
            List of GuardResult objects from all executed guards.
        """
        # Initialize the results collection for this pipeline run.
        results: list[GuardResult] = []
        # Log the start of pipeline execution with input details.
        logger.debug("input_pipeline_execution_started", text_length=len(text))
        # Iterate through each guard in the configured execution order.
        for guard in self._guards:
            # Skip guards that are disabled in configuration.
            if not guard.enabled:
                logger.debug("guard_skipped_disabled", guard_name=guard.name)
                continue
            # Execute the guard evaluation and handle potential errors.
            try:
                # Run the async guard evaluation on the input text.
                result = await guard.evaluate(text, context)
                # Add the guard result to the pipeline results collection.
                results.append(result)
                # Short-circuit pipeline if guard returns BLOCK action.
                if result.action == GuardAction.BLOCK.value:
                    # Log the pipeline short-circuit with blocking guard name.
                    logger.info(
                        "input_pipeline_blocked",
                        guard_name=guard.name,
                        message=result.message,
                    )
                    # Stop executing remaining guards after a block.
                    break
            except Exception as e:
                # Log unexpected guard execution errors as error events.
                logger.error(
                    "guard_execution_error",
                    guard_name=guard.name,
                    error=str(e),
                )
                # Create a failure result for the errored guard.
                results.append(
                    GuardResult(
                        guard_name=guard.name,
                        passed=False,
                        action=GuardAction.BLOCK.value,
                        severity="critical",
                        message=f"Guard execution error: {type(e).__name__}",
                        confidence=1.0,
                        details={"error": str(e)},
                    )
                )
                # Short-circuit on guard error for safety.
                break
        # Log pipeline completion with result summary information.
        logger.debug(
            "input_pipeline_execution_completed",
            total_guards_run=len(results),
            all_passed=all(r.passed for r in results),
        )
        # Return the complete list of guard evaluation results.
        return results


class OutputPipeline:
    """Pipeline that runs output guards sequentially on LLM responses.

    Guards execute in order. Supports text modification through redaction
    guards that transform the output while allowing it to proceed.
    """

    def __init__(self, guards: list[BaseGuard]) -> None:
        """Initialize output pipeline with an ordered list of guards.

        Args:
            guards: Ordered list of output guard instances to execute.
        """
        # Store the ordered guard list for sequential execution.
        self._guards = guards
        # Log the pipeline initialization with guard count.
        logger.info("output_pipeline_initialized", guard_count=len(guards))

    async def execute(
        self, text: str, context: dict[str, Any] | None = None
    ) -> tuple[list[GuardResult], str]:
        """Execute all enabled output guards on LLM response text.

        Runs guards sequentially, applying text modifications from
        redaction guards and short-circuiting on BLOCK action.

        Args:
            text: LLM output text to evaluate through the guard chain.
            context: Optional context dictionary passed to each guard.

        Returns:
            Tuple of (guard results list, potentially modified output text).
        """
        # Initialize the results collection for this pipeline run.
        results: list[GuardResult] = []
        # Track the current text state as redaction guards modify it.
        current_text = text
        # Log the start of output pipeline execution.
        logger.debug("output_pipeline_execution_started", text_length=len(text))
        # Iterate through each guard in the configured execution order.
        for guard in self._guards:
            # Skip guards that are disabled in configuration.
            if not guard.enabled:
                logger.debug("guard_skipped_disabled", guard_name=guard.name)
                continue
            # Execute the guard evaluation and handle potential errors.
            try:
                # Run the async guard evaluation on the current text state.
                result = await guard.evaluate(current_text, context)
                # Add the guard result to the pipeline results collection.
                results.append(result)
                # Apply text modifications if guard produced redacted output.
                if result.modified_text is not None:
                    # Update current text with the redacted version.
                    current_text = result.modified_text
                    # Log the text modification event for auditing.
                    logger.debug("output_text_modified", guard_name=guard.name)
                # Short-circuit pipeline if guard returns BLOCK action.
                if result.action == GuardAction.BLOCK.value:
                    # Log the pipeline short-circuit with blocking guard name.
                    logger.info(
                        "output_pipeline_blocked",
                        guard_name=guard.name,
                        message=result.message,
                    )
                    # Stop executing remaining guards after a block.
                    break
            except Exception as e:
                # Log unexpected guard execution errors as error events.
                logger.error(
                    "guard_execution_error",
                    guard_name=guard.name,
                    error=str(e),
                )
                # Create a failure result for the errored guard.
                results.append(
                    GuardResult(
                        guard_name=guard.name,
                        passed=False,
                        action=GuardAction.BLOCK.value,
                        severity="critical",
                        message=f"Guard execution error: {type(e).__name__}",
                        confidence=1.0,
                        details={"error": str(e)},
                    )
                )
                # Short-circuit on guard error for safety.
                break
        # Log pipeline completion with result summary information.
        logger.debug(
            "output_pipeline_execution_completed",
            total_guards_run=len(results),
            text_modified=(current_text != text),
        )
        # Return results and the potentially modified output text.
        return results, current_text
