"""
PII redaction guard for LLM output.
Scans generated responses and replaces detected PII with redaction characters.
Unlike the input PII detector which blocks, this guard sanitizes output in-place.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import PII_PATTERNS  # Pre-compiled PII regex patterns.
from guardrails.utils.text_processor import TextProcessor  # Text redaction utilities.

# Module-level logger instance for PII redaction events.
logger = get_logger(__name__)


class PIIRedactorGuard(BaseGuard):
    """Redacts personally identifiable information from LLM output text.

    Scans output for PII patterns and replaces them with configurable
    redaction characters, preserving the overall text structure.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize PII redactor with redaction configuration.

        Args:
            config: Guard settings including redaction character and types.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load the character used for redacting PII content.
        self._redaction_char = config.get("redaction_char", "*")
        # Load minimum redaction segment length for consistency.
        self._min_redaction_length = config.get("min_redaction_length", 4)
        # Load PII types to redact, ordered longest-pattern-first to prevent overlap.
        default_order = ["credit_card", "ssn", "email", "phone", "ip_address"]
        # Use configured order, falling back to optimal detection order.
        self._redact_types = config.get("redact_types", default_order)

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate LLM output text and redact any PII found.

        Args:
            text: LLM generated output text to scan and redact.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult with redacted text in modified_text field if PII found.
        """
        # Log the start of PII redaction evaluation at debug level.
        logger.debug("pii_redaction_started", text_length=len(text))
        # Track the current text state as redactions are applied.
        redacted_text = text
        # Count total number of PII instances redacted across all types.
        total_redactions = 0
        # Track which PII types were found and redacted in the output.
        redacted_types: list[str] = []
        # Iterate through each configured PII type for redaction.
        for pii_type in self._redact_types:
            # Skip PII types that don't have a corresponding pattern.
            if pii_type not in PII_PATTERNS:
                continue
            # Get the pre-compiled regex pattern for this PII type.
            pattern = PII_PATTERNS[pii_type]
            # Count matches before redaction to track what was found.
            matches = pattern.findall(redacted_text)
            # Apply redaction if any matches were found for this type.
            if matches:
                # Redact all pattern matches using the configured character.
                redacted_text = TextProcessor.redact_match(
                    redacted_text, pattern, self._redaction_char
                )
                # Increment the total redaction counter by matches found.
                total_redactions += len(matches)
                # Record this PII type as having been redacted.
                redacted_types.append(pii_type)
        # Determine if any redactions were applied to the output text.
        if total_redactions > 0:
            # Log the redaction event with details for auditing purposes.
            logger.info(
                "pii_redacted_from_output",
                redaction_count=total_redactions,
                redacted_types=redacted_types,
            )
            # Return result with redacted action and modified text content.
            return GuardResult(
                guard_name=self.name,
                passed=True,
                action=GuardAction.REDACT.value,
                severity=Severity.MEDIUM.value,
                message=f"PII redacted from output: {', '.join(redacted_types)}",
                confidence=0.9,
                details={
                    "redacted_types": redacted_types,
                    "redaction_count": total_redactions,
                },
                modified_text=redacted_text,
            )
        # No PII found in output — return passing result unchanged.
        logger.debug("pii_redaction_passed", text_length=len(text))
        # Return passing result indicating no redaction was needed.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No PII found in output",
            confidence=0.0,
            details={},
        )
