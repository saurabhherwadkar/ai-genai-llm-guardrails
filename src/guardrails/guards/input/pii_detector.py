"""
PII (Personally Identifiable Information) detection guard.
Scans input text for email addresses, phone numbers, SSNs,
credit card numbers, and IP addresses using compiled regex patterns.
"""

from typing import Any  # Generic type for flexible dictionary values.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.core.interfaces import BaseGuard, GuardAction, Severity  # Guard contracts.
from guardrails.models.guard_result import GuardResult  # Evaluation result structure.
from guardrails.utils.regex_patterns import PII_PATTERNS  # Pre-compiled PII regex patterns.

# Module-level logger instance for PII detection events.
logger = get_logger(__name__)


class PIIDetectorGuard(BaseGuard):
    """Detects personally identifiable information in user input text.

    Scans for configurable PII types using regex pattern matching.
    Returns detailed results about which PII types were found and where.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize PII detector with detection configuration.

        Args:
            config: Guard settings including threshold and PII types.
        """
        # Call parent constructor to set enabled state and store config.
        super().__init__(config)
        # Load the confidence threshold from configuration (default 0.8).
        self._threshold = config.get("confidence_threshold", 0.8)
        # Load the action to take when PII is detected (block or warn).
        self._action = config.get("action", "block")
        # Load the list of PII types to detect from configuration.
        self._detect_types = config.get("detect_types", list(PII_PATTERNS.keys()))

    async def evaluate(self, text: str, context: dict[str, Any] | None = None) -> GuardResult:
        """Evaluate input text for the presence of PII patterns.

        Args:
            text: User input text to scan for PII content.
            context: Optional context dictionary for evaluation decisions.

        Returns:
            GuardResult indicating whether PII was detected and details.
        """
        # Log the start of PII detection evaluation at debug level.
        logger.debug("pii_detection_started", text_length=len(text))
        # Initialize collection for tracking detected PII instances.
        detected_pii: dict[str, list[str]] = {}
        # Iterate through each configured PII type for detection.
        for pii_type in self._detect_types:
            # Skip PII types that don't have a corresponding pattern.
            if pii_type not in PII_PATTERNS:
                continue
            # Get the pre-compiled regex pattern for this PII type.
            pattern = PII_PATTERNS[pii_type]
            # Find all matches of this PII pattern in the input text.
            matches = pattern.findall(text)
            # Record any detected matches for this PII type.
            if matches:
                detected_pii[pii_type] = matches
        # Determine result based on whether any PII was detected.
        if detected_pii:
            # Calculate confidence based on number and variety of detections.
            total_matches = sum(len(v) for v in detected_pii.values())
            # Higher confidence when multiple types detected simultaneously.
            confidence = min(1.0, 0.7 + (total_matches * 0.1))
            # Only flag if confidence exceeds the configured threshold.
            if confidence >= self._threshold:
                # Log the PII detection event with details for auditing.
                logger.warning(
                    "pii_detected",
                    pii_types=list(detected_pii.keys()),
                    match_count=total_matches,
                )
                # Return blocking or warning result based on configured action.
                return GuardResult(
                    guard_name=self.name,
                    passed=False,
                    action=self._action,
                    severity=Severity.HIGH.value,
                    message=f"PII detected: {', '.join(detected_pii.keys())}",
                    confidence=confidence,
                    details={
                        "detected_types": list(detected_pii.keys()),
                        "match_count": total_matches,
                    },
                )
        # No PII detected — return passing result with zero confidence.
        logger.debug("pii_detection_passed", text_length=len(text))
        # Content is clean, return passing guard result.
        return GuardResult(
            guard_name=self.name,
            passed=True,
            action=GuardAction.PASS.value,
            severity=Severity.LOW.value,
            message="No PII detected in input",
            confidence=0.0,
            details={},
        )
