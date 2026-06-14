"""
PII vault for reversible tokenization.
Replaces PII in input text with unique placeholder tokens before sending
to the LLM, then restores original values in the output. This prevents
the LLM from ever seeing real PII while preserving context.
"""

import uuid
from typing import Any

import regex

from guardrails.config.logging_config import get_logger
from guardrails.utils.regex_patterns import PII_PATTERNS

logger = get_logger(__name__)

# Prefix/suffix used to make placeholders unlikely to collide with real text.
_TOKEN_PREFIX = "<PII_"
_TOKEN_SUFFIX = ">"


class PIIVault:
    """Stores a bidirectional mapping between PII values and placeholder tokens.

    Usage:
        vault = PIIVault(detect_types=["email", "phone"])
        sanitized = vault.tokenize(user_input)
        # send sanitized text to LLM ...
        restored = vault.detokenize(llm_output)
    """

    def __init__(self, detect_types: list[str] | None = None) -> None:
        self._detect_types = detect_types or list(PII_PATTERNS.keys())
        # Maps placeholder token -> original PII value.
        self._token_to_value: dict[str, str] = {}
        # Maps original PII value -> placeholder token (avoids duplicate tokens for same value).
        self._value_to_token: dict[str, str] = {}

    @property
    def token_map(self) -> dict[str, str]:
        """Return a copy of the placeholder-to-original mapping."""
        return dict(self._token_to_value)

    @property
    def has_pii(self) -> bool:
        """Whether any PII was found during tokenization."""
        return len(self._token_to_value) > 0

    def tokenize(self, text: str) -> str:
        """Replace all detected PII in text with placeholder tokens.

        Each unique PII value gets a stable token — if the same email
        appears twice, both occurrences get the same placeholder.
        """
        result = text
        for pii_type in self._detect_types:
            if pii_type not in PII_PATTERNS:
                continue
            pattern = PII_PATTERNS[pii_type]
            matches = pattern.findall(result)
            for match in matches:
                if match in self._value_to_token:
                    token = self._value_to_token[match]
                else:
                    token = self._generate_token(pii_type)
                    self._token_to_value[token] = match
                    self._value_to_token[match] = token
                result = result.replace(match, token, 1)

        if self._token_to_value:
            logger.info(
                "pii_vault_tokenized",
                token_count=len(self._token_to_value),
                pii_types=list({self._extract_type(t) for t in self._token_to_value}),
            )
        return result

    def detokenize(self, text: str) -> str:
        """Restore all placeholder tokens in text with original PII values."""
        result = text
        for token, value in self._token_to_value.items():
            result = result.replace(token, value)

        if self._token_to_value:
            logger.debug("pii_vault_detokenized", token_count=len(self._token_to_value))
        return result

    def _generate_token(self, pii_type: str) -> str:
        short_id = uuid.uuid4().hex[:8]
        return f"{_TOKEN_PREFIX}{pii_type.upper()}_{short_id}{_TOKEN_SUFFIX}"

    @staticmethod
    def _extract_type(token: str) -> str:
        """Extract the PII type from a token string for logging."""
        inner = token.removeprefix(_TOKEN_PREFIX).removesuffix(_TOKEN_SUFFIX)
        return inner.rsplit("_", 1)[0].lower() if "_" in inner else inner.lower()
