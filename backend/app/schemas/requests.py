"""Request schemas for the AI Product Manager API."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProductIdeaRequest(BaseModel):
    """A product idea to run through the agent pipeline."""

    idea: str = Field(..., min_length=10, max_length=2000, description="The product idea")
    thread_id: Optional[str] = Field(None, description="Reuse a thread to build on earlier runs")
    depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description=(
            "quick: 4 agents on the fast model, no review. "
            "standard: 6 agents with a quality review. "
            "deep: adds a refinement pass over artifacts that fail review."
        ),
    )

    @field_validator("idea")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("Product idea must be at least 10 characters of actual content")
        return cleaned


class ValidationRequest(BaseModel):
    """An idea to sanity-check before spending a full pipeline run on it."""

    idea: str = Field(..., min_length=1, max_length=2000)


class KnowledgeSearchRequest(BaseModel):
    """Direct query against the retrieval corpus."""

    query: str = Field(..., min_length=2, max_length=500)
    k: int = Field(default=5, ge=1, le=10)
    domain: Optional[str] = Field(None, description="Restrict to one knowledge domain")


class ExportRequest(BaseModel):
    """Export a plan the client already holds.

    The plan travels in the request rather than being regenerated server-side:
    re-running the pipeline for an export would cost another full set of LLM
    calls and could return a different document than the one on screen.
    """

    plan: Dict[str, Any] = Field(..., description="A payload previously returned by /generate")
    idea: Optional[str] = Field(None, max_length=2000, description="Original idea, for the document header")

    @field_validator("plan")
    @classmethod
    def _has_content(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not any(value.get(key) for key in ("plan", "prd", "architecture", "tickets")):
            raise ValueError("plan must contain at least one of: plan, prd, architecture, tickets")
        return value
