"""
Text processing utility class.
Provides normalization, sanitization, and text manipulation methods
used across multiple guardrail implementations.
"""

import regex  # Enhanced regex library for pattern-based text operations.


class TextProcessor:
    """Utility class for text normalization and sanitization.

    All methods are static — no instance state required.
    Designed for memory-efficient string operations.
    """

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse multiple whitespace characters into single spaces.

        Args:
            text: Raw input text with potentially irregular spacing.

        Returns:
            Text with normalized single-space separation.
        """
        # Replace any sequence of whitespace characters with a single space.
        return regex.sub(r"\s+", " ", text).strip()

    @staticmethod
    def to_lowercase(text: str) -> str:
        """Convert text to lowercase for case-insensitive comparison.

        Args:
            text: Text in any case mixture.

        Returns:
            Fully lowercase version of the input text.
        """
        # Convert entire string to lowercase characters.
        return text.lower()

    @staticmethod
    def remove_special_characters(text: str) -> str:
        """Remove non-alphanumeric characters except basic punctuation.

        Args:
            text: Text potentially containing special or control characters.

        Returns:
            Text with only letters, numbers, spaces, and basic punctuation.
        """
        # Keep only word characters, whitespace, and common punctuation marks.
        return regex.sub(r"[^\w\s.,!?;:'\"-]", "", text)

    @staticmethod
    def truncate(text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis indicator.

        Args:
            text: Text that may exceed the maximum allowed length.
            max_length: Maximum number of characters to retain.

        Returns:
            Original text if within limit, truncated with ellipsis otherwise.
        """
        # Return unchanged if text is within the allowed length limit.
        if len(text) <= max_length:
            return text
        # Truncate and append ellipsis to indicate content was cut.
        return text[:max_length] + "..."

    @staticmethod
    def redact_match(text: str, pattern: regex.Pattern, redaction_char: str = "*") -> str:
        """Replace all regex matches in text with redaction characters.

        Args:
            text: Text containing sensitive content to redact.
            pattern: Compiled regex pattern identifying content to redact.
            redaction_char: Character to use for replacing sensitive text.

        Returns:
            Text with all pattern matches replaced by redaction characters.
        """

        # Replace each match with redaction characters of the same length.
        def _replace(match: regex.Match) -> str:
            # Generate redaction string matching the original match length.
            return redaction_char * len(match.group())

        # Apply the replacement function to all pattern matches in text.
        return pattern.sub(_replace, text)

    @staticmethod
    def count_tokens_approximate(text: str) -> int:
        """Estimate token count using whitespace-based approximation.

        This is a rough estimate — actual tokenization depends on the model.
        Approximately 4 characters per token for English text.

        Args:
            text: Text to estimate token count for.

        Returns:
            Approximate number of tokens in the text.
        """
        # Estimate tokens as character count divided by average chars per token.
        return max(1, len(text) // 4)

    @staticmethod
    def contains_unicode_tricks(text: str) -> bool:
        """Detect Unicode homoglyph attacks and invisible characters.

        These are sometimes used to bypass text-based filters.

        Args:
            text: Text to check for Unicode manipulation attempts.

        Returns:
            True if suspicious Unicode usage is detected.
        """
        # Check for zero-width characters commonly used in obfuscation.
        zero_width_chars = "​‌‍⁠﻿"
        # Return True if any zero-width obfuscation character is present.
        for char in zero_width_chars:
            if char in text:
                return True
        # Check for text direction override characters used in spoofing.
        direction_overrides = "‪‫‬‭‮"
        # Return True if directional override characters are present.
        for char in direction_overrides:
            if char in text:
                return True
        # No suspicious Unicode manipulation detected in the text.
        return False
