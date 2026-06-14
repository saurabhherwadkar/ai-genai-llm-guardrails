"""Unit tests for PII vault tokenization and detokenization."""

import pytest

from guardrails.utils.pii_vault import PIIVault


class TestPIIVault:
    def test_tokenize_email(self):
        vault = PIIVault(detect_types=["email"])
        text = "Contact me at john@example.com for details"
        result = vault.tokenize(text)

        assert "john@example.com" not in result
        assert "<PII_EMAIL_" in result
        assert vault.has_pii is True

    def test_tokenize_phone(self):
        vault = PIIVault(detect_types=["phone"])
        text = "Call me at 555-123-4567"
        result = vault.tokenize(text)

        assert "555-123-4567" not in result
        assert "<PII_PHONE_" in result

    def test_tokenize_ssn(self):
        vault = PIIVault(detect_types=["ssn"])
        text = "My SSN is 123-45-6789"
        result = vault.tokenize(text)

        assert "123-45-6789" not in result
        assert "<PII_SSN_" in result

    def test_tokenize_credit_card(self):
        vault = PIIVault(detect_types=["credit_card"])
        text = "Card number 4111111111111111"
        result = vault.tokenize(text)

        assert "4111111111111111" not in result
        assert "<PII_CREDIT_CARD_" in result

    def test_detokenize_restores_original(self):
        vault = PIIVault(detect_types=["email"])
        original = "Send to john@example.com and cc jane@example.com"
        tokenized = vault.tokenize(original)

        assert "john@example.com" not in tokenized
        assert "jane@example.com" not in tokenized

        restored = vault.detokenize(tokenized)
        assert restored == original

    def test_same_value_gets_same_token(self):
        vault = PIIVault(detect_types=["email"])
        text = "Email john@example.com and again john@example.com"
        result = vault.tokenize(text)

        tokens = [t for t in result.split() if t.startswith("<PII_")]
        assert len(tokens) == 2
        assert tokens[0] == tokens[1]

    def test_detokenize_in_llm_output(self):
        vault = PIIVault(detect_types=["email"])
        vault.tokenize("My email is user@test.com")

        token = list(vault.token_map.keys())[0]
        llm_response = f"I see your email is {token}, I'll send it there."
        restored = vault.detokenize(llm_response)

        assert "user@test.com" in restored
        assert token not in restored

    def test_no_pii_returns_unchanged(self):
        vault = PIIVault()
        text = "Hello, what is the weather today?"
        result = vault.tokenize(text)

        assert result == text
        assert vault.has_pii is False

    def test_multiple_pii_types(self):
        vault = PIIVault(detect_types=["email", "phone"])
        text = "Reach me at bob@acme.org or 800-555-1234"
        tokenized = vault.tokenize(text)

        assert "bob@acme.org" not in tokenized
        assert "800-555-1234" not in tokenized

        restored = vault.detokenize(tokenized)
        assert "bob@acme.org" in restored
        assert "800-555-1234" in restored

    def test_token_map_property(self):
        vault = PIIVault(detect_types=["email"])
        vault.tokenize("test@example.com")

        token_map = vault.token_map
        assert len(token_map) == 1
        assert list(token_map.values())[0] == "test@example.com"
