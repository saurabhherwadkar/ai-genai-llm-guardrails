"""
Output content filter guard.
Filters LLM-generated responses for inappropriate, harmful, or
policy-violating content before returning to the user.
"""

from typing import Any  # Generic type for flexible dictionary values.

import regex  # Enhanced regex library for pattern matching.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import TOXIC_KEYWORDS  # Content keyword dictionary.
from guardrails.utils.text_processor import TextProcessor  # Text normalization utilities.

# Module-level logger instance for content filtering events.
logger = get_logger(__name__)

# Pattern matching content that provides harmful instructions.
HARMFUL_INSTRUCTION_PATTERN = regex.compile(
    r"(?:step\s*\d+|first|then|next|finally).*?"  # Instruction sequence indicators.
    r"(?:mix|combine|inject|insert|attach|connect)",  # Action verbs for harmful steps.
    regex.IGNORECASE,
)

# Pattern matching content that reveals system-level information.
SYSTEM_LEAK_PATTERN = regex.compile(
    r"my\s+(?:system\s+)?(?:prompt|instructions)\s+(?:are|say|tell)"  # Prompt leaking.
    r"|"
    r"I\s+(?:was|am)\s+(?:programmed|instructed|told)\s+to"  # System instruction reveal.
    r"|"
    r"(?:system|initial)\s+(?:prompt|instruction|message)",  # Direct prompt reference.
    regex.IGNORECASE,
)


class ContentFilterGuard(BaseGuard):
    """Filters inappropriate or harmful content from LLM output.

    Applies multiple checks including toxic content detection,
    harmful instruction identification, and system information leakage.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize content filter with threshold and action configuration.

        Args:
            config: Guard settings including confidence threshold and action.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load confidence threshold for filtering content.
        self._threshold = config.get("confidence_threshold", 0.75)
        # Load the action to take when inappropriate content is found.
        self._action = config.get("action", "block")

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate LLM output for inappropriate or harmful content.

        Checks for toxic language, harmful instructions, and system leaks.

        Args:
            text: LLM generated output text to filter for harmful content.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult indicating whether output content is acceptable.
        """
        # Log the start of content filter evaluation at debug level.
        logger.debug("content_filter_started", text_length=len(text))
        # Initialize confidence score for inappropriate content detection.
        confidence = 0.0
        # Collect all reasons content was flagged as inappropriate.
        violations: list[str] = []
        # Normalize text for consistent case-insensitive matching.
        normalized_text = TextProcessor.to_lowercase(text)
        # Check output for toxic content keywords across all categories.
        for category, keywords in TOXIC_KEYWORDS.items():
            # Build pattern from keywords for this toxic category.
            pattern_str = "|".join(regex.escape(kw) for kw in keywords)
            # Compile and search for toxic keywords in normalized text.
            matches = regex.findall(pattern_str, normalized_text, regex.IGNORECASE)
            # Flag if toxic keywords from any category are found in output.
            if matches:
                # Toxic content in output significantly increases confidence.
                confidence += 0.5
                # Record the toxic category violation for reporting.
                violations.append(f"Toxic content ({category}): {len(matches)} matches")
        # Check for content that provides harmful step-by-step instructions.
        if HARMFUL_INSTRUCTION_PATTERN.search(text):
            # Harmful instructions are a moderate content concern.
            confidence += 0.3
            # Record the harmful instruction pattern detection.
            violations.append("Potentially harmful instructions detected")
        # Check for content that leaks system prompt or instructions.
        if SYSTEM_LEAK_PATTERN.search(text):
            # System information leakage is a significant security concern.
            confidence += 0.5
            # Record the system information leakage detection.
            violations.append("System prompt/instruction leakage detected")
        # Cap confidence at 1.0 maximum value.
        confidence = min(1.0, confidence)
        # Determine if confidence exceeds the configured threshold.
        if confidence >= self._threshold:
            # Log the content filter trigger as a warning event.
            logger.warning(
                "content_filter_triggered",
                confidence=confidence,
                violations=violations,
            )
            # Return blocking result with content violation details.
            return GuardResult(
                guard_name=self.name,
                passed=False,
                action=self._action,
                severity=Severity.HIGH.value,
                message="Inappropriate content detected in LLM output",
                confidence=confidence,
                details={"violations": violations},
            )
        # Output content passes all filter checks successfully.
        logger.debug("content_filter_passed", text_length=len(text))
        # Return passing result indicating output is appropriate.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="Output content passes filter checks",
            confidence=confidence,
            details={},
        )
