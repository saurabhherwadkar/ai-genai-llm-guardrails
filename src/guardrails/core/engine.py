"""
Guardrail orchestration engine.
Coordinates the full validation flow: input guards -> LLM call -> output guards.
Assembles guards from configuration and manages the complete request lifecycle.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.config.settings import load_guardrails_config  # Config loaders.
from guardrails.core.interfaces import BaseGuard, BaseLLMProvider, GuardAction  # Contracts.
from guardrails.core.pipeline import InputPipeline, OutputPipeline  # Pipeline runners.
from guardrails.guards.input import (  # Input guard implementations.
    PIIDetectorGuard,
    PromptInjectionGuard,
    TopicRestrictionGuard,
    ToxicContentGuard,
)
from guardrails.guards.output import (  # Output guard implementations.
    ContentFilterGuard,
    HallucinationGuard,
    OutputValidatorGuard,
    PIIRedactorGuard,
)
from guardrails.models.guard_result import GuardResult  # Result data structure.
from guardrails.models.responses import GuardrailResponse  # API response structure.
from guardrails.utils.pii_vault import PIIVault  # Reversible PII tokenization.

# Module-level logger instance for engine orchestration events.
logger = get_logger(__name__)


class GuardrailEngine:
    """Central orchestration engine for the guardrail validation system.

    Assembles input and output guard pipelines from configuration,
    coordinates the full request lifecycle, and produces structured responses.
    """

    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        """Initialize the engine with configuration and optional LLM provider.

        Args:
            llm_provider: Optional LLM provider for generating responses.
        """
        # Store the LLM provider reference for generating responses.
        self._llm_provider = llm_provider
        # Load guardrail-specific configuration from YAML file.
        self._guardrails_config = load_guardrails_config()
        # Build the input guard pipeline from configuration.
        self._input_pipeline = self._build_input_pipeline()
        # Build the output guard pipeline from configuration.
        self._output_pipeline = self._build_output_pipeline()
        # Log engine initialization with pipeline sizes.
        logger.info(
            "guardrail_engine_initialized",
            llm_provider=llm_provider.provider_name if llm_provider else "none",
        )

    def _build_input_pipeline(self) -> InputPipeline:
        """Assemble input guards from configuration into a pipeline.

        Returns:
            Configured InputPipeline with all enabled input guards.
        """
        # Get input guard configurations from the guardrails config.
        input_config = self._guardrails_config.get("input_guards", {})
        # Initialize the ordered list of input guard instances.
        guards: list[BaseGuard] = []
        # Create PII detector guard from its configuration section.
        pii_config = input_config.get("pii_detector", {})
        # Add PII detector to the pipeline guard list.
        guards.append(PIIDetectorGuard(pii_config))
        # Create prompt injection guard from its configuration section.
        injection_config = input_config.get("prompt_injection", {})
        # Add prompt injection detector to the pipeline guard list.
        guards.append(PromptInjectionGuard(injection_config))
        # Create toxic content guard from its configuration section.
        toxic_config = input_config.get("toxic_content", {})
        # Add toxic content detector to the pipeline guard list.
        guards.append(ToxicContentGuard(toxic_config))
        # Create topic restriction guard from its configuration section.
        topic_config = input_config.get("topic_restriction", {})
        # Add topic restriction guard to the pipeline guard list.
        guards.append(TopicRestrictionGuard(topic_config))
        # Return the assembled input pipeline with all configured guards.
        return InputPipeline(guards)

    def _build_output_pipeline(self) -> OutputPipeline:
        """Assemble output guards from configuration into a pipeline.

        Returns:
            Configured OutputPipeline with all enabled output guards.
        """
        # Get output guard configurations from the guardrails config.
        output_config = self._guardrails_config.get("output_guards", {})
        # Initialize the ordered list of output guard instances.
        guards: list[BaseGuard] = []
        # Create PII redactor guard from its configuration section.
        pii_config = output_config.get("pii_redactor", {})
        # Add PII redactor to the pipeline guard list.
        guards.append(PIIRedactorGuard(pii_config))
        # Create hallucination detector from its configuration section.
        hallucination_config = output_config.get("hallucination_detector", {})
        # Add hallucination detector to the pipeline guard list.
        guards.append(HallucinationGuard(hallucination_config))
        # Create content filter guard from its configuration section.
        filter_config = output_config.get("content_filter", {})
        # Add content filter to the pipeline guard list.
        guards.append(ContentFilterGuard(filter_config))
        # Create output validator guard from its configuration section.
        validator_config = output_config.get("output_validator", {})
        # Add output validator to the pipeline guard list.
        guards.append(OutputValidatorGuard(validator_config))
        # Return the assembled output pipeline with all configured guards.
        return OutputPipeline(guards)

    async def validate_input(
        self, text: str, context: dict[str, Any] | None = None
    ) -> list[GuardResult]:
        """Run input text through the input guardrail pipeline.

        Args:
            text: User input text to validate against all input guards.
            context: Optional context dictionary for guard evaluation.

        Returns:
            List of GuardResult objects from input pipeline execution.
        """
        # Log the start of input validation with text length.
        logger.info("input_validation_started", text_length=len(text))
        # Execute the input pipeline and return its results.
        return await self._input_pipeline.execute(text, context)

    async def validate_output(
        self, text: str, context: dict[str, Any] | None = None
    ) -> tuple[list[GuardResult], str]:
        """Run LLM output through the output guardrail pipeline.

        Args:
            text: LLM generated output text to validate and sanitize.
            context: Optional context dictionary for guard evaluation.

        Returns:
            Tuple of (guard results list, potentially modified output text).
        """
        # Log the start of output validation with text length.
        logger.info("output_validation_started", text_length=len(text))
        # Execute the output pipeline and return results with modified text.
        return await self._output_pipeline.execute(text, context)

    async def process_request(
        self,
        input_text: str,
        context: dict[str, Any] | None = None,
        process_with_llm: bool = False,
        output_schema: dict[str, Any] | None = None,
    ) -> GuardrailResponse:
        """Process a complete guardrail request through the full pipeline.

        Validates input, optionally calls LLM, validates output,
        and assembles the final structured response.

        Args:
            input_text: User input text to validate and optionally process.
            context: Optional context dictionary for evaluation decisions.
            process_with_llm: Whether to generate LLM response after input validation.
            output_schema: Optional JSON schema for validating structured output.

        Returns:
            Complete GuardrailResponse with all validation results.
        """
        # Log the start of full request processing.
        logger.info("request_processing_started", text_length=len(input_text))
        # Execute input validation pipeline on the user's text.
        input_results = await self.validate_input(input_text, context)
        # Determine overall input pipeline action from results.
        input_blocked = any(r.action == GuardAction.BLOCK.value for r in input_results)
        # If input is blocked, return response without LLM processing.
        if input_blocked:
            # Log that the request was blocked at input validation stage.
            logger.warning("request_blocked_at_input", input_text_length=len(input_text))
            # Build and return the blocked response without LLM output.
            return GuardrailResponse(
                allowed=False,
                overall_action=GuardAction.BLOCK.value,
                input_results=input_results,
                output_results=[],
                input_text=input_text,
                output_text=None,
                summary="Request blocked by input guardrails",
            )
        # If LLM processing not requested, return input-only validation results.
        if not process_with_llm or not self._llm_provider:
            # Determine if any warnings exist in input results.
            has_warnings = any(r.action == GuardAction.WARN.value for r in input_results)
            # Set action to warn if warnings present, pass otherwise.
            action = GuardAction.WARN.value if has_warnings else GuardAction.PASS.value
            # Return response with input validation results only.
            return GuardrailResponse(
                allowed=True,
                overall_action=action,
                input_results=input_results,
                output_results=[],
                input_text=input_text,
                output_text=None,
                summary="Input validation completed successfully",
            )
        # Tokenize PII in input before sending to LLM.
        vault_config = self._guardrails_config.get("pii_vault", {})
        pii_vault = PIIVault(detect_types=vault_config.get("detect_types"))
        sanitized_input = pii_vault.tokenize(input_text) if vault_config.get("enabled", False) else input_text
        # Generate LLM response since input passed all guards.
        try:
            # Call the configured LLM provider with PII-free input.
            llm_output = await self._llm_provider.generate(sanitized_input)
            # Log successful LLM response generation.
            logger.info("llm_response_generated", output_length=len(llm_output))
        except Exception as e:
            # Log LLM generation failure as an error event.
            logger.error("llm_generation_failed", error=str(e))
            # Return error response if LLM call fails.
            return GuardrailResponse(
                allowed=False,
                overall_action=GuardAction.BLOCK.value,
                input_results=input_results,
                output_results=[],
                input_text=input_text,
                output_text=None,
                summary=f"LLM generation failed: {type(e).__name__}",
            )
        # Build context for output validation including schema if provided.
        output_context = context.copy() if context else {}
        # Add output schema to context for validator guard usage.
        if output_schema:
            output_context["output_schema"] = output_schema
        # Execute output validation pipeline on the LLM response.
        output_results, final_text = await self.validate_output(llm_output, output_context)
        # Determine overall output pipeline action from results.
        output_blocked = any(r.action == GuardAction.BLOCK.value for r in output_results)
        # Determine if any warnings exist across all results.
        has_warnings = any(
            r.action == GuardAction.WARN.value for r in input_results + output_results
        )
        # Restore original PII values in output if vault has tokens.
        if pii_vault.has_pii:
            final_text = pii_vault.detokenize(final_text)
        # Determine the final overall action for the complete request.
        if output_blocked:
            # Output was blocked — return with block action and no output.
            overall_action = GuardAction.BLOCK.value
            allowed = False
            summary = "Response blocked by output guardrails"
            final_output = None
        elif has_warnings:
            # Warnings present but not blocked — allow with warning status.
            overall_action = GuardAction.WARN.value
            allowed = True
            summary = "Request processed with warnings"
            final_output = final_text
        else:
            # Everything passed cleanly — return with pass action.
            overall_action = GuardAction.PASS.value
            allowed = True
            summary = "Request processed successfully"
            final_output = final_text
        # Log the completion of full request processing.
        logger.info(
            "request_processing_completed",
            allowed=allowed,
            overall_action=overall_action,
        )
        # Build and return the complete guardrail response.
        return GuardrailResponse(
            allowed=allowed,
            overall_action=overall_action,
            input_results=input_results,
            output_results=output_results,
            input_text=input_text,
            output_text=final_output,
            summary=summary,
        )
