"""
Topic restriction guard.
Enforces content boundaries by blocking requests about explicitly
prohibited topics such as illegal activities, weapons, or drug synthesis.
"""

from typing import Any  # Generic type for flexible dictionary values.

import regex  # Enhanced regex library for Unicode-aware pattern matching.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import BLOCKED_TOPIC_KEYWORDS  # Topic keyword dictionary.
from guardrails.utils.text_processor import TextProcessor  # Text normalization utilities.

# Module-level logger instance for topic restriction detection events.
logger = get_logger(__name__)


class TopicRestrictionGuard(BaseGuard):
    """Enforces topic boundaries by blocking content about prohibited subjects.

    Checks user input against a configurable list of blocked topics
    using keyword pattern matching with case-insensitive comparison.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize topic restriction guard with topic configuration.

        Args:
            config: Guard settings including blocked and allowed topics.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load the action to take when blocked topic is detected.
        self._action = config.get("action", "warn")
        # Load explicitly blocked topic categories from configuration.
        self._blocked_topics = config.get("blocked_topics", list(BLOCKED_TOPIC_KEYWORDS.keys()))
        # Load allowed topics list (empty means no topic allowlisting).
        self._allowed_topics = config.get("allowed_topics", [])
        # Pre-compile patterns for efficient repeated matching.
        self._compiled_patterns = self._compile_topic_patterns()

    def _compile_topic_patterns(self) -> dict[str, regex.Pattern]:
        """Compile regex patterns for each blocked topic category.

        Returns:
            Dictionary mapping topic names to compiled detection patterns.
        """
        # Initialize dictionary for storing compiled patterns per topic.
        patterns: dict[str, regex.Pattern] = {}
        # Iterate through each blocked topic to compile its keywords.
        for topic in self._blocked_topics:
            # Skip topics that don't have defined detection keywords.
            if topic not in BLOCKED_TOPIC_KEYWORDS:
                continue
            # Get the keyword list for this blocked topic category.
            keywords = BLOCKED_TOPIC_KEYWORDS[topic]
            # Compile all keywords into a single alternation pattern.
            pattern_str = "|".join(regex.escape(kw) for kw in keywords)
            # Store the compiled case-insensitive pattern for this topic.
            patterns[topic] = regex.compile(pattern_str, regex.IGNORECASE)
        # Return the dictionary of compiled patterns for all topics.
        return patterns

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate input text against topic restriction rules.

        Args:
            text: User input text to check against topic boundaries.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult indicating whether a blocked topic was detected.
        """
        # Log the start of topic restriction evaluation at debug level.
        logger.debug("topic_restriction_started", text_length=len(text))
        # Normalize text for consistent case-insensitive matching.
        normalized_text = TextProcessor.to_lowercase(text)
        # Track which blocked topics were triggered by the input.
        triggered_topics: dict[str, list[str]] = {}
        # Iterate through each compiled topic pattern for matching.
        for topic, pattern in self._compiled_patterns.items():
            # Find all keyword matches for this blocked topic.
            matches = pattern.findall(normalized_text)
            # Record matches if any keywords from this topic were found.
            if matches:
                triggered_topics[topic] = matches
        # Determine result based on whether blocked topics were detected.
        if triggered_topics:
            # Calculate confidence based on match strength and variety.
            total_matches = sum(len(v) for v in triggered_topics.values())
            # High confidence when blocked topic keywords are clearly present.
            confidence = min(1.0, 0.75 + (total_matches * 0.1))
            # Log the blocked topic detection as a warning event.
            logger.warning(
                "blocked_topic_detected",
                topics=list(triggered_topics.keys()),
                confidence=confidence,
            )
            # Return result with the configured action for topic violations.
            return GuardResult(
                guard_name=self.name,
                passed=False,
                action=self._action,
                severity=Severity.HIGH.value,
                message=f"Blocked topic detected: {', '.join(triggered_topics.keys())}",
                confidence=confidence,
                details={
                    "triggered_topics": list(triggered_topics.keys()),
                    "match_count": total_matches,
                },
            )
        # No blocked topics detected — input is within allowed boundaries.
        logger.debug("topic_restriction_passed", text_length=len(text))
        # Return passing result indicating topic is acceptable.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No restricted topics detected",
            confidence=0.0,
            details={},
        )
