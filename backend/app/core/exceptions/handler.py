"""
Global exception handler for the AI Product Manager application.
"""
import logging
from typing import Union
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .custom import BaseProductManagerException
from ..logging.logger import app_logger


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Handle exceptions globally."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(exc, request)
    
    async def _handle_exception(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle and format exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log the exception
        app_logger.error(
            f"Unhandled exception in request {request_id}: {str(exc)}",
            request_id=request_id,
            path=str(request.url),
            method=request.method,
            exception_type=type(exc).__name__,
            exception_message=str(exc)
        )
        
        # Format response based on exception type
        if isinstance(exc, BaseProductManagerException):
            return self._handle_product_manager_exception(exc, request_id)
        elif isinstance(exc, HTTPException):
            return self._handle_http_exception(exc, request_id)
        else:
            return self._handle_generic_exception(exc, request_id)
    
    def _handle_product_manager_exception(self, exc: BaseProductManagerException, request_id: str) -> JSONResponse:
        """Handle custom product manager exceptions."""
        status_code = self._get_status_code_for_exception(exc)
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "request_id": request_id,
                    "details": exc.details
                }
            }
        )
    
    def _handle_http_exception(self, exc: HTTPException, request_id: str) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_EXCEPTION",
                    "message": exc.detail,
                    "request_id": request_id,
                    "details": {"status_code": exc.status_code}
                }
            }
        )
    
    def _handle_generic_exception(self, exc: Exception, request_id: str) -> JSONResponse:
        """Handle generic exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "details": {
                        "exception_type": type(exc).__name__,
                        "debug_message": str(exc) if app_logger.logger.level <= logging.DEBUG else None
                    }
                }
            }
        )
    
    def _get_status_code_for_exception(self, exc: BaseProductManagerException) -> int:
        """Map exception types to HTTP status codes."""
        exception_mapping = {
            "ValidationError": 400,
            "AgentExecutionError": 500,
            "AgentTimeoutError": 504,
            "AgentRetryExhaustedError": 500,
            "WorkflowExecutionError": 500,
            "MemorySystemError": 500,
            "ExportError": 500,
            "ConfigurationError": 500,
            "RateLimitError": 429,
        }
        
        return exception_mapping.get(exc.error_code, 500)


async def create_request_id_middleware(request: Request, call_next):
    """Middleware to add request ID to request state."""
    import uuid
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
