"""
Prompt injection detection guard.
Identifies attempts to manipulate LLM behavior through injected instructions,
role-playing attacks, and instruction override patterns.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import INJECTION_PATTERN  # Pre-compiled injection regex.
from guardrails.utils.text_processor import TextProcessor  # Text normalization utilities.

# Module-level logger instance for injection detection events.
logger = get_logger(__name__)


class PromptInjectionGuard(BaseGuard):
    """Detects prompt injection attacks in user input text.

    Uses pattern matching and heuristic analysis to identify attempts
    to override system instructions, extract prompts, or manipulate behavior.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize injection detector with detection configuration.

        Args:
            config: Guard settings including threshold and max length.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load confidence threshold for flagging injection attempts.
        self._threshold = config.get("confidence_threshold", 0.7)
        # Load the action to take on detection (block or warn).
        self._action = config.get("action", "block")
        # Load maximum allowed prompt length to prevent resource abuse.
        self._max_prompt_length = config.get("max_prompt_length", 10000)

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate input text for prompt injection attempts.

        Checks for known injection patterns, excessive length,
        and Unicode obfuscation techniques.

        Args:
            text: User input text to analyze for injection patterns.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult indicating whether injection was detected.
        """
        # Log the start of injection detection analysis at debug level.
        logger.debug("injection_detection_started", text_length=len(text))
        # Initialize confidence score and detection reasons list.
        confidence = 0.0
        # Collect all reasons that contribute to injection suspicion.
        reasons: list[str] = []
        # Check if the input exceeds maximum allowed prompt length.
        if len(text) > self._max_prompt_length:
            # Excessive length is a weak injection indicator.
            confidence += 0.3
            # Record the reason for audit trail and debugging.
            reasons.append(
                f"Prompt exceeds maximum length ({len(text)} > {self._max_prompt_length})"
            )
        # Normalize text to lowercase for case-insensitive pattern matching.
        normalized_text = TextProcessor.to_lowercase(text)
        # Search for known injection keyword patterns in normalized text.
        injection_matches = INJECTION_PATTERN.findall(normalized_text)
        # Calculate confidence contribution from keyword matches.
        if injection_matches:
            # Each unique match increases confidence significantly.
            match_confidence = min(0.9, 0.4 + len(injection_matches) * 0.2)
            # Add keyword match confidence to running total.
            confidence += match_confidence
            # Record detected injection patterns for the audit details.
            reasons.append(f"Injection patterns detected: {injection_matches[:5]}")
        # Check for Unicode obfuscation tricks that bypass text filters.
        if TextProcessor.contains_unicode_tricks(text):
            # Unicode tricks are a moderate injection indicator.
            confidence += 0.3
            # Record Unicode manipulation detection reason.
            reasons.append("Unicode obfuscation characters detected")
        # Check for excessive special character density indicating encoding attacks.
        special_char_ratio = self._calculate_special_char_ratio(text)
        # Flag unusually high special character density as suspicious.
        if special_char_ratio > 0.4:
            # High special character ratio suggests encoded payload.
            confidence += 0.2
            # Record the special character density finding.
            reasons.append(f"High special character density: {special_char_ratio:.2f}")
        # Cap confidence at 1.0 maximum value.
        confidence = min(1.0, confidence)
        # Determine if confidence exceeds the configured threshold.
        if confidence >= self._threshold:
            # Log the injection detection as a security warning event.
            logger.warning(
                "prompt_injection_detected",
                confidence=confidence,
                reasons=reasons,
            )
            # Return blocking result with injection detection details.
            return GuardResult(
                guard_name=self.name,
                passed=False,
                action=self._action,
                severity=Severity.CRITICAL.value,
                message="Potential prompt injection detected",
                confidence=confidence,
                details={"reasons": reasons},
            )
        # No injection detected — input appears safe for processing.
        logger.debug("injection_detection_passed", confidence=confidence)
        # Return passing result indicating no injection was found.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No prompt injection detected",
            confidence=confidence,
            details={},
        )

    @staticmethod
    def _calculate_special_char_ratio(text: str) -> float:
        """Calculate the ratio of special characters to total characters.

        Args:
            text: Input text to analyze for special character density.

        Returns:
            Float ratio between 0.0 and 1.0 of special characters.
        """
        # Return zero ratio for empty text to avoid division by zero.
        if not text:
            return 0.0
        # Count characters that are not alphanumeric or whitespace.
        special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        # Calculate and return the ratio of special to total characters.
        return special_count / len(text)
