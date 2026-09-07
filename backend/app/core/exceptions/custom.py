"""Application exceptions.

Transport-level LLM failures live in `app.llm.errors`; agent and graph failures
in `app.agents.base` and `app.orchestration.graph`. These cover the remaining
application concerns.
"""
from typing import Any, Dict, Optional


class ProductManagerError(Exception):
    """Base for application errors, carrying a code and structured details."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(ProductManagerError):
    """Configuration is missing or invalid."""


class ExportError(ProductManagerError):
    """An export could not be rendered."""


class MemorySystemError(ProductManagerError):
    """Memory persistence failed."""
