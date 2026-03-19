"""
Request schemas for the AI Product Manager API.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class ProductIdeaRequest(BaseModel):
    """Request model for product idea generation."""
    
    idea: str = Field(..., min_length=10, max_length=2000, description="Product idea description")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    use_legacy: Optional[bool] = Field(False, description="Use legacy workflow")
    
    @validator('idea')
    def validate_idea(cls, v):
        """Validate product idea content."""
        if not v.strip():
            raise ValueError("Product idea cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Product idea must be at least 10 characters long")
        return v.strip()


class BatchRequest(BaseModel):
    """Request model for batch processing."""
    
    ideas: List[str] = Field(..., min_items=1, max_items=10, description="List of product ideas")
    thread_id: Optional[str] = Field(None, description="Thread ID for batch continuity")
    use_legacy: Optional[bool] = Field(False, description="Use legacy workflow")
    
    @validator('ideas')
    def validate_ideas(cls, v):
        """Validate list of ideas."""
        if not v:
            raise ValueError("At least one idea is required")
        validated_ideas = []
        for idea in v:
            if not idea.strip():
                raise ValueError("Ideas cannot be empty")
            if len(idea.strip()) < 10:
                raise ValueError("Each idea must be at least 10 characters long")
            validated_ideas.append(idea.strip())
        return validated_ideas


class ExportRequest(BaseModel):
    """Request model for export functionality."""
    
    idea: str = Field(..., min_length=10, max_length=2000, description="Product idea for export")
    thread_id: Optional[str] = Field(None, description="Thread ID for context")
    export_type: str = Field(..., description="Export type: pdf, csv, json")
    
    @validator('export_type')
    def validate_export_type(cls, v):
        """Validate export type."""
        allowed_types = ['pdf', 'csv', 'json']
        if v.lower() not in allowed_types:
            raise ValueError(f"Export type must be one of: {', '.join(allowed_types)}")
        return v.lower()


class ValidationRequest(BaseModel):
    """Request model for product idea validation."""
    
    idea: str = Field(..., min_length=10, max_length=2000, description="Product idea to validate")
    thread_id: Optional[str] = Field(None, description="Thread ID for context")


class ThreadRequest(BaseModel):
    """Request model for thread operations."""
    
    thread_id: str = Field(..., description="Thread ID")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of entries to retrieve")
