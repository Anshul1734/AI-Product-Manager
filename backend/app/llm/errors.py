"""Typed LLM failures, so callers can distinguish retryable from terminal errors."""


class LLMError(RuntimeError):
    """Base class for all LLM transport/protocol failures."""


class LLMNotConfiguredError(LLMError):
    """No usable API key. Terminal: retrying cannot help."""


class LLMRateLimitError(LLMError):
    """Provider returned 429. Retryable after `retry_after` seconds."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMServerError(LLMError):
    """Provider returned 5xx or the connection failed. Retryable."""


class LLMBadRequestError(LLMError):
    """Provider rejected the request (4xx other than 429). Terminal."""


class LLMResponseFormatError(LLMError):
    """Response body was not shaped the way the API contract promises."""
