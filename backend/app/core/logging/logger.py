"""
Structured logging system for the AI Product Manager application.
"""
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager

from ..config.settings import settings


class StructuredLogger:
    """Structured logger with JSON formatting and correlation tracking."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logger with appropriate handlers and formatters."""
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Formatter based on settings
        if settings.LOG_FORMAT.lower() == "json":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method with structured data."""
        extra_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            **kwargs
        }
        
        getattr(self.logger, level)(message, extra={"structured_data": extra_data})
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        self._log("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self._log("debug", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data."""
        self._log("critical", message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add structured data if available
        if hasattr(record, 'structured_data'):
            log_data.update(record.structured_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class RequestLogger:
    """Request-scoped logger with correlation tracking."""
    
    def __init__(self, logger: StructuredLogger, request_id: Optional[str] = None):
        self.logger = logger
        self.request_id = request_id or str(uuid.uuid4())
        self.start_time = time.time()
    
    def log_request_start(self, method: str, path: str, **kwargs):
        """Log request start."""
        self.logger.info(
            f"Request started: {method} {path}",
            request_id=self.request_id,
            method=method,
            path=path,
            **kwargs
        )
    
    def log_request_end(self, status_code: int, **kwargs):
        """Log request completion."""
        duration = time.time() - self.start_time
        self.logger.info(
            f"Request completed: {status_code}",
            request_id=self.request_id,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_request_error(self, error: Exception, **kwargs):
        """Log request error."""
        duration = time.time() - self.start_time
        self.logger.error(
            f"Request failed: {str(error)}",
            request_id=self.request_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )


class AgentLogger:
    """Agent-specific logger for tracking agent execution."""
    
    def __init__(self, logger: StructuredLogger, agent_name: str, request_id: Optional[str] = None):
        self.logger = logger
        self.agent_name = agent_name
        self.request_id = request_id or str(uuid.uuid4())
    
    def log_agent_start(self, input_data: Any, **kwargs):
        """Log agent execution start."""
        self.logger.info(
            f"Agent {self.agent_name} started",
            request_id=self.request_id,
            agent_name=self.agent_name,
            agent_input=str(input_data)[:1000],  # Truncate long inputs
            **kwargs
        )
    
    def log_agent_success(self, output_data: Any, **kwargs):
        """Log agent successful execution."""
        self.logger.info(
            f"Agent {self.agent_name} completed successfully",
            request_id=self.request_id,
            agent_name=self.agent_name,
            agent_output_length=len(str(output_data)),
            **kwargs
        )
    
    def log_agent_error(self, error: Exception, retry_count: int = 0, **kwargs):
        """Log agent execution error."""
        self.logger.error(
            f"Agent {self.agent_name} failed: {str(error)}",
            request_id=self.request_id,
            agent_name=self.agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            retry_count=retry_count,
            **kwargs
        )
    
    def log_agent_retry(self, retry_count: int, **kwargs):
        """Log agent retry attempt."""
        self.logger.warning(
            f"Agent {self.agent_name} retry attempt {retry_count}",
            request_id=self.request_id,
            agent_name=self.agent_name,
            retry_count=retry_count,
            **kwargs
        )


@contextmanager
def request_context(logger: StructuredLogger, method: str, path: str, **kwargs):
    """Context manager for request logging."""
    request_logger = RequestLogger(logger)
    request_logger.log_request_start(method, path, **kwargs)
    
    try:
        yield request_logger
        request_logger.log_request_end(200)
    except Exception as e:
        request_logger.log_request_error(e)
        raise


@contextmanager
def agent_context(logger: StructuredLogger, agent_name: str, input_data: Any, request_id: Optional[str] = None):
    """Context manager for agent execution logging."""
    agent_logger = AgentLogger(logger, agent_name, request_id)
    agent_logger.log_agent_start(input_data)
    
    try:
        yield agent_logger
        agent_logger.log_agent_success("success")
    except Exception as e:
        agent_logger.log_agent_error(e)
        raise


# Global logger instance
app_logger = StructuredLogger("ai_product_manager")
