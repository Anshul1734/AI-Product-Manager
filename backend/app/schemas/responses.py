"""
Response schemas for the AI Product Manager API.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model."""
    
    success: bool = Field(..., description="Request success status")
    message: Optional[str] = Field(None, description="Response message")
    request_id: Optional[str] = Field(None, description="Request correlation ID")


class HealthResponse(BaseResponse):
    """Health check response."""
    
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    uptime: Optional[str] = Field(None, description="Service uptime")
    components: Optional[Dict[str, str]] = Field(None, description="Component health status")


class WorkflowResponse(BaseResponse):
    """Workflow execution response."""
    
    data: Optional[Dict[str, Any]] = Field(None, description="Workflow execution data")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    thread_id: Optional[str] = Field(None, description="Thread ID for continuity")
    quality_score: Optional[float] = Field(None, description="Output quality score")
    improvements_made: Optional[bool] = Field(None, description="Whether improvements were made")


class ValidationResponse(BaseResponse):
    """Product idea validation response."""
    
    valid: bool = Field(..., description="Validation result")
    issues: List[str] = Field(default_factory=list, description="Validation issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    confidence_score: Optional[float] = Field(None, description="Validation confidence")


class BatchResponse(BaseResponse):
    """Batch processing response."""
    
    results: List[WorkflowResponse] = Field(..., description="Batch execution results")
    total_processed: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Successful executions")
    failed: int = Field(..., description="Failed executions")
    total_execution_time: float = Field(..., description="Total execution time")


class AnalyticsResponse(BaseResponse):
    """Analytics data response."""
    
    total_requests: int = Field(..., description="Total requests processed")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    average_execution_time: float = Field(..., description="Average execution time")
    popular_ideas: List[Dict[str, Any]] = Field(default_factory=list, description="Popular product ideas")
    error_rates: Dict[str, float] = Field(default_factory=dict, description="Error rates by type")


class ThreadResponse(BaseResponse):
    """Thread operations response."""
    
    thread_id: str = Field(..., description="Thread ID")
    entries: List[Dict[str, Any]] = Field(..., description="Thread entries")
    total_entries: int = Field(..., description="Total entries in thread")
    thread_summary: Optional[Dict[str, Any]] = Field(None, description="Thread summary")


class ExportResponse(BaseResponse):
    """Export operation response."""
    
    export_type: str = Field(..., description="Type of export")
    filename: str = Field(..., description="Generated filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Download URL")


class ErrorResponse(BaseResponse):
    """Error response model."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
