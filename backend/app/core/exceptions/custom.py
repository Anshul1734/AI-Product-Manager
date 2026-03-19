"""
Custom exceptions for the AI Product Manager application.
"""
from typing import Any, Dict, Optional


class BaseProductManagerException(Exception):
    """Base exception for all custom exceptions."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class ValidationError(BaseProductManagerException):
    """Raised when input validation fails."""
    pass


class AgentExecutionError(BaseProductManagerException):
    """Raised when agent execution fails."""
    pass


class AgentTimeoutError(BaseProductManagerException):
    """Raised when agent execution times out."""
    pass


class AgentRetryExhaustedError(BaseProductManagerException):
    """Raised when agent retries are exhausted."""
    pass


class WorkflowExecutionError(BaseProductManagerException):
    """Raised when workflow execution fails."""
    pass


class MemorySystemError(BaseProductManagerException):
    """Raised when memory system operations fail."""
    pass


class ExportError(BaseProductManagerException):
    """Raised when export operations fail."""
    pass


class ConfigurationError(BaseProductManagerException):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(BaseProductManagerException):
    """Raised when rate limit is exceeded."""
    pass
