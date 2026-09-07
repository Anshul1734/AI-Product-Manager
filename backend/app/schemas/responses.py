"""Response schemas for the AI Product Manager API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class WorkflowResponse(BaseResponse):
    """Result of a pipeline run."""

    data: Optional[Dict[str, Any]] = Field(None, description="Plan, PRD, architecture, tickets, trace and metadata")
    execution_time: Optional[float] = None
    thread_id: Optional[str] = None
    error_type: Optional[str] = Field(None, description="Exception class name, when success is false")


class ValidationResponse(BaseResponse):
    valid: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class KnowledgeSearchResponse(BaseResponse):
    query: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    retrievers: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, Any] = Field(default_factory=dict)
