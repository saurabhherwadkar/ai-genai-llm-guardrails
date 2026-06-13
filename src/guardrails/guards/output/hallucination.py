"""
Hallucination detection guard for LLM output.
Identifies potentially fabricated claims, unsupported statistics,
and factual assertions that may not be grounded in reality.
"""

from typing import Any  # Generic type for flexible dictionary values.

import regex  # Enhanced regex library for pattern matching.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.

# Module-level logger instance for hallucination detection events.
logger = get_logger(__name__)

# Pattern matching specific statistical claims that may be fabricated.
STATISTIC_PATTERN = regex.compile(
    r"\b\d+(?:\.\d+)?%\s+of\b"  # Matches "X% of" statistical claims.
    r"|"
    r"\bstudies\s+show\b"  # Matches "studies show" authority claims.
    r"|"
    r"\baccording\s+to\s+research\b"  # Matches vague research citations.
    r"|"
    r"\bscientists\s+have\s+proven\b"  # Matches unattributed proof claims.
    r"|"
    r"\bit\s+is\s+a\s+fact\s+that\b",  # Matches assertion-as-fact phrases.
    regex.IGNORECASE,
)

# Pattern matching confident assertion language without qualifiers.
CONFIDENCE_ASSERTION_PATTERN = regex.compile(
    r"\bdefinitely\b"  # Absolute certainty without hedging.
    r"|"
    r"\balways\b"  # Universal claim without exceptions.
    r"|"
    r"\bnever\b"  # Absolute negation without nuance.
    r"|"
    r"\bevery\s+single\b"  # Emphatic universal claim.
    r"|"
    r"\bwithout\s+exception\b"  # Explicit exclusion of alternatives.
    r"|"
    r"\bundeniably\b"  # Asserting undeniable truth.
    r"|"
    r"\bguaranteed\b",  # Promise or guarantee language.
    regex.IGNORECASE,
)

# Pattern matching fabricated citation formats.
FAKE_CITATION_PATTERN = regex.compile(
    r"\(\w+\s+et\s+al\.,?\s*\d{4}\)"  # Matches "(Author et al., 2024)" style.
    r"|"
    r"Journal\s+of\s+\w+"  # Matches generic "Journal of X" references.
    r"|"
    r"published\s+in\s+\d{4}",  # Matches "published in YYYY" without source.
    regex.IGNORECASE,
)


class HallucinationGuard(BaseGuard):
    """Detects potential hallucinations in LLM-generated output.

    Uses heuristic analysis of statistical claims, confidence assertions,
    and citation patterns to flag potentially fabricated content.
    Note: This is pattern-based detection, not factual verification.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize hallucination detector with threshold configuration.

        Args:
            config: Guard settings including confidence threshold and action.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load confidence threshold for flagging hallucination risk.
        self._threshold = config.get("confidence_threshold", 0.6)
        # Load the action to take when hallucination is suspected.
        self._action = config.get("action", "warn")

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate LLM output for signs of hallucinated content.

        Checks for unsupported statistics, overconfident assertions,
        and potentially fabricated citations.

        Args:
            text: LLM generated output text to analyze for hallucination.
            context: Optional context with source documents for grounding.

        Returns:
            GuardResult indicating hallucination risk assessment.
        """
        # Log the start of hallucination detection at debug level.
        logger.debug("hallucination_detection_started", text_length=len(text))
        # Initialize confidence score for hallucination indicators.
        confidence = 0.0
        # Collect all indicators that suggest hallucinated content.
        indicators: list[str] = []
        # Check for unattributed statistical claims in the output.
        stat_matches = STATISTIC_PATTERN.findall(text)
        # Statistical claims without proper attribution increase risk.
        if stat_matches:
            # Each unattributed statistic contributes to hallucination score.
            confidence += min(0.5, 0.2 + len(stat_matches) * 0.15)
            # Record the statistical claim indicators found.
            indicators.append(f"Unattributed statistics found: {len(stat_matches)}")
        # Check for overconfident assertion language without hedging.
        assertion_matches = CONFIDENCE_ASSERTION_PATTERN.findall(text)
        # Absolute language suggests potential overconfidence in claims.
        if assertion_matches:
            # Each confident assertion contributes to hallucination score.
            confidence += min(0.5, 0.15 + len(assertion_matches) * 0.1)
            # Record the overconfident assertion indicators found.
            indicators.append(f"Overconfident assertions: {len(assertion_matches)}")
        # Check for potentially fabricated academic citations.
        citation_matches = FAKE_CITATION_PATTERN.findall(text)
        # Fabricated citations are a strong hallucination indicator.
        if citation_matches:
            # Citations without verification contribute significantly.
            confidence += min(0.5, 0.25 + len(citation_matches) * 0.2)
            # Record the unverified citation indicators found.
            indicators.append(f"Unverified citations: {len(citation_matches)}")
        # Cap confidence at 1.0 maximum value.
        confidence = min(1.0, confidence)
        # Determine if confidence exceeds the configured threshold.
        if confidence >= self._threshold:
            # Log the hallucination risk detection as a warning event.
            logger.warning(
                "hallucination_risk_detected",
                confidence=confidence,
                indicators=indicators,
            )
            # Return warning result with hallucination risk details.
            return GuardResult(
                guard_name=self.name,
                passed=False,
                action=self._action,
                severity=Severity.MEDIUM.value,
                message="Potential hallucination indicators detected in output",
                confidence=confidence,
                details={"indicators": indicators},
            )
        # No significant hallucination indicators found in the output.
        logger.debug("hallucination_detection_passed", confidence=confidence)
        # Return passing result indicating acceptable hallucination risk.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No significant hallucination indicators detected",
            confidence=confidence,
            details={},
        )
