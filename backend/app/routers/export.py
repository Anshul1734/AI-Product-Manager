"""
Export endpoints.

These take the plan payload the client already holds and render a file from it.
No regeneration, so an export is fast, free, and byte-for-byte consistent with
what the user is looking at.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Response

from ..schemas.requests import ExportRequest
from ..services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])
service = ExportService()


def _attachment(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.post("/prd/markdown")
async def export_prd_markdown(request: ExportRequest) -> Response:
    """Full PRD as Markdown."""
    try:
        content = service.prd_markdown(request.plan, request.idea)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not render PRD: {exc}") from exc
    return _attachment(content, service.filename(request.plan, "prd", "md"), "text/markdown; charset=utf-8")


@router.post("/tickets/csv")
async def export_tickets_csv(request: ExportRequest) -> Response:
    """Backlog as Jira-importable CSV."""
    if not (request.plan.get("tickets") or {}).get("epics"):
        raise HTTPException(status_code=422, detail="This plan contains no tickets to export")
    try:
        content = service.tickets_csv(request.plan)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not render CSV: {exc}") from exc
    return _attachment(content, service.filename(request.plan, "tickets", "csv"), "text/csv; charset=utf-8")


@router.post("/full/json")
async def export_full_json(request: ExportRequest) -> Response:
    """Everything, including the agent trace and citations."""
    try:
        content = service.full_json(request.plan, request.idea)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not render JSON: {exc}") from exc
    return _attachment(content, service.filename(request.plan, "full", "json"), "application/json")


@router.get("/formats")
async def formats() -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "formats": [
                {
                    "type": "markdown",
                    "name": "PRD (Markdown)",
                    "description": "Complete requirements document, ready to paste into Notion, Confluence or a repo",
                    "endpoint": "/api/v1/export/prd/markdown",
                },
                {
                    "type": "csv",
                    "name": "Backlog (Jira CSV)",
                    "description": "Epics, stories and tasks as importable rows",
                    "endpoint": "/api/v1/export/tickets/csv",
                },
                {
                    "type": "json",
                    "name": "Full plan (JSON)",
                    "description": "Every artifact plus the agent trace and retrieval citations",
                    "endpoint": "/api/v1/export/full/json",
                },
                {
                    "type": "pdf",
                    "name": "PDF",
                    "description": "Use your browser's Print / Save as PDF on the results view",
                    "endpoint": None,
                },
            ]
        },
    }
