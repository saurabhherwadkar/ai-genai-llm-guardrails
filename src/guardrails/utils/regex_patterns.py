"""
Pre-compiled regex patterns for PII and content detection.
Patterns are compiled once at module load for maximum runtime efficiency.
All patterns use the enhanced 'regex' library for Unicode support.
"""

import regex  # Enhanced regex library with Unicode category support.

# Email address pattern matching standard formats (user@domain.tld).
EMAIL_PATTERN = regex.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# US phone number patterns matching various common formats.
PHONE_PATTERN = regex.compile(
    r"(?:\+?1[-.\s]?)?"  # Optional country code prefix for US numbers.
    r"(?:\(?\d{3}\)?[-.\s]?)"  # Area code with optional parentheses.
    r"\d{3}[-.\s]?"  # Exchange number with optional separator.
    r"\d{4}"  # Subscriber number completing the phone number.
)

# US Social Security Number pattern (XXX-XX-XXXX format).
SSN_PATTERN = regex.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")

# Credit card number pattern matching major card formats (13-19 digits).
CREDIT_CARD_PATTERN = regex.compile(
    r"\b(?:"
    r"4[0-9]{12}(?:[0-9]{3})?"  # Visa cards starting with 4.
    r"|5[1-5][0-9]{14}"  # Mastercard cards starting with 51-55.
    r"|3[47][0-9]{13}"  # American Express starting with 34 or 37.
    r"|6(?:011|5[0-9]{2})[0-9]{12}"  # Discover cards starting with 6011 or 65.
    r")\b"
)

# IPv4 address pattern matching dotted decimal notation.
IP_ADDRESS_PATTERN = regex.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"  # First three octets.
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"  # Final octet of IPv4 address.
)

# Dictionary mapping PII type names to their compiled detection patterns.
PII_PATTERNS: dict[str, regex.Pattern] = {
    "email": EMAIL_PATTERN,
    "phone": PHONE_PATTERN,
    "ssn": SSN_PATTERN,
    "credit_card": CREDIT_CARD_PATTERN,
    "ip_address": IP_ADDRESS_PATTERN,
}

# Common prompt injection indicators and manipulation keywords.
INJECTION_KEYWORDS: list[str] = [
    "ignore previous instructions",  # Direct override attempt.
    "ignore all previous",  # Variant of instruction override.
    "disregard above",  # Instruction nullification attempt.
    "forget everything",  # Memory reset manipulation.
    "you are now",  # Role reassignment manipulation.
    "act as",  # Role-playing injection attempt.
    "pretend you are",  # Identity override manipulation.
    "new instructions",  # Instruction replacement attempt.
    "system prompt",  # System prompt extraction attempt.
    "reveal your instructions",  # Prompt leaking attempt.
    "override",  # Generic override keyword.
    "bypass",  # Security bypass attempt indicator.
    "jailbreak",  # Explicit jailbreak attempt keyword.
    "do anything now",  # DAN-style jailbreak pattern.
    "developer mode",  # Developer mode activation attempt.
]

# Compiled pattern matching any injection keyword (case-insensitive).
INJECTION_PATTERN = regex.compile(
    "|".join(regex.escape(kw) for kw in INJECTION_KEYWORDS),
    regex.IGNORECASE,
)

# Toxic content keyword categories for basic detection.
TOXIC_KEYWORDS: dict[str, list[str]] = {
    "hate_speech": [
        "racial slur",  # Placeholder — real implementations use ML models.
        "ethnic slur",  # Ethnic targeting language indicator.
    ],
    "harassment": [
        "kill yourself",  # Direct harassment language.
        "die in a fire",  # Violent threat language.
        "hope you die",  # Death wish harassment.
    ],
    "violence": [
        "how to murder",  # Murder instruction seeking.
        "how to kill",  # Killing instruction request.
        "make a bomb",  # Weapon creation instructions.
        "build explosives",  # Explosive creation request.
    ],
    "self_harm": [
        "how to commit suicide",  # Self-harm instruction seeking.
        "best way to end my life",  # Suicide method request.
        "ways to hurt myself",  # Self-injury instruction.
    ],
    "sexual_content": [
        "explicit sexual",  # Explicit sexual content marker.
        "pornographic",  # Pornography reference marker.
    ],
}

# Blocked topic keywords for topic restriction enforcement.
BLOCKED_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "illegal_activities": [
        "how to hack",  # Unauthorized access instruction.
        "steal money",  # Theft planning language.
        "launder money",  # Money laundering instruction.
        "forge documents",  # Document forgery request.
    ],
    "weapons_manufacturing": [
        "build a gun",  # Firearm construction request.
        "3d print weapon",  # Weapon printing instruction.
        "make ammunition",  # Ammunition creation request.
    ],
    "drug_synthesis": [
        "synthesize methamphetamine",  # Drug synthesis instruction.
        "cook meth",  # Drug manufacturing slang.
        "make fentanyl",  # Opioid synthesis request.
        "grow marijuana illegally",  # Illegal cultivation request.
    ],
}
