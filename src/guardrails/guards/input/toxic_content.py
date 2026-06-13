"""
Toxic content detection guard.
Identifies harmful, hateful, violent, or otherwise inappropriate content
in user input using keyword matching and pattern analysis.
"""

from typing import Any  # Generic type for flexible dictionary values.

import regex  # Enhanced regex library for Unicode-aware pattern matching.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import TOXIC_KEYWORDS  # Toxic content keyword dictionary.
from guardrails.utils.text_processor import TextProcessor  # Text normalization utilities.

# Module-level logger instance for toxic content detection events.
logger = get_logger(__name__)


class ToxicContentGuard(BaseGuard):
    """Detects toxic, harmful, or inappropriate content in user input.

    Scans for configurable categories of toxic content including
    hate speech, harassment, violence, self-harm, and sexual content.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize toxic content detector with category configuration.

        Args:
            config: Guard settings including categories and threshold.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load confidence threshold for flagging toxic content.
        self._threshold = config.get("confidence_threshold", 0.75)
        # Load the action to take when toxicity is detected.
        self._action = config.get("action", "block")
        # Load the categories of toxic content to detect.
        self._categories = config.get("categories", list(TOXIC_KEYWORDS.keys()))
        # Pre-compile category patterns for efficient repeated matching.
        self._compiled_patterns = self._compile_category_patterns()

    def _compile_category_patterns(self) -> dict[str, regex.Pattern]:
        """Compile regex patterns for each enabled toxic content category.

        Returns:
            Dictionary mapping category names to compiled regex patterns.
        """
        # Initialize dictionary for storing compiled patterns per category.
        patterns: dict[str, regex.Pattern] = {}
        # Iterate through each enabled category to compile its keywords.
        for category in self._categories:
            # Skip categories that don't have defined keywords.
            if category not in TOXIC_KEYWORDS:
                continue
            # Get the keyword list for this toxic content category.
            keywords = TOXIC_KEYWORDS[category]
            # Compile all keywords into a single alternation pattern.
            pattern_str = "|".join(regex.escape(kw) for kw in keywords)
            # Store the compiled case-insensitive pattern for this category.
            patterns[category] = regex.compile(pattern_str, regex.IGNORECASE)
        # Return the dictionary of compiled patterns for all categories.
        return patterns

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate input text for toxic content across configured categories.

        Args:
            text: User input text to scan for toxic content.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult indicating whether toxic content was detected.
        """
        # Log the start of toxic content evaluation at debug level.
        logger.debug("toxic_content_detection_started", text_length=len(text))
        # Normalize text for consistent case-insensitive matching.
        normalized_text = TextProcessor.to_lowercase(text)
        # Track which categories triggered with their matched keywords.
        triggered_categories: dict[str, list[str]] = {}
        # Iterate through each compiled pattern for category matching.
        for category, pattern in self._compiled_patterns.items():
            # Find all matches of this category's keywords in the text.
            matches = pattern.findall(normalized_text)
            # Record matches if any keywords from this category were found.
            if matches:
                triggered_categories[category] = matches
        # Determine result based on whether any toxic content was found.
        if triggered_categories:
            # Calculate confidence based on number of triggered categories.
            category_count = len(triggered_categories)
            # More categories triggered means higher confidence of toxicity.
            total_matches = sum(len(v) for v in triggered_categories.values())
            # Confidence increases with both category variety and match count.
            confidence = min(1.0, 0.6 + (category_count * 0.15) + (total_matches * 0.05))
            # Only flag if confidence exceeds the configured threshold.
            if confidence >= self._threshold:
                # Log the toxic content detection as a warning event.
                logger.warning(
                    "toxic_content_detected",
                    categories=list(triggered_categories.keys()),
                    confidence=confidence,
                )
                # Return blocking result with toxicity detection details.
                return GuardResult(
                    guard_name=self.name,
                    passed=False,
                    action=self._action,
                    severity=Severity.HIGH.value,
                    message=(
                        f"Toxic content detected in categories: "
                        f"{', '.join(triggered_categories.keys())}"
                    ),
                    confidence=confidence,
                    details={
                        "triggered_categories": list(triggered_categories.keys()),
                        "match_count": total_matches,
                    },
                )
        # No toxic content detected — input appears safe and appropriate.
        logger.debug("toxic_content_detection_passed", text_length=len(text))
        # Return passing result indicating content is clean.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No toxic content detected",
            confidence=0.0,
            details={},
        )
