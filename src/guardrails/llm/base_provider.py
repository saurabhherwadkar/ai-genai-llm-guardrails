"""
Base LLM provider module.
Re-exports the abstract base class from core interfaces for convenience.
Provider implementations should import from here rather than core directly.
"""

from guardrails.core.interfaces import BaseLLMProvider  # noqa: F401  # Abstract provider base.
