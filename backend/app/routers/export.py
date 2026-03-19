"""
Export router for the AI Product Manager API.
"""
import io
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from ..core import app_logger, request_context
from ..schemas import ExportRequest
from ..services import ExportService


router = APIRouter()
export_service = ExportService()


@router.post("/export/prd/pdf")
async def export_prd_pdf(request: ExportRequest):
    """Export PRD as downloadable PDF."""
    async with request_context(app_logger, "POST", "/export/prd/pdf", export_type="pdf"):
        try:
            pdf_bytes = await export_service.export_prd_pdf(request)
            filename = export_service.generate_filename("PRD", "pdf")
            
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
            )
            
        except Exception as e:
            app_logger.error(
                "PRD PDF export failed",
                export_type="pdf",
                thread_id=request.thread_id,
                error=str(e)
            )
            raise HTTPException(status_code=500, detail=f"Failed to export PRD as PDF: {str(e)}")


@router.post("/export/tickets/csv")
async def export_tickets_csv(request: ExportRequest):
    """Export tickets as Jira-compatible CSV."""
    async with request_context(app_logger, "POST", "/export/tickets/csv", export_type="csv"):
        try:
            csv_bytes = await export_service.export_tickets_csv(request)
            filename = export_service.generate_filename("tickets", "csv")
            
            return Response(
                content=csv_bytes,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
            )
            
        except Exception as e:
            app_logger.error(
                "Tickets CSV export failed",
                export_type="csv",
                thread_id=request.thread_id,
                error=str(e)
            )
            raise HTTPException(status_code=500, detail=f"Failed to export tickets as CSV: {str(e)}")


@router.post("/export/full/json")
async def export_full_json(request: ExportRequest):
    """Export complete workflow as JSON."""
    async with request_context(app_logger, "POST", "/export/full/json", export_type="json"):
        try:
            json_bytes = await export_service.export_full_json(request)
            filename = export_service.generate_filename("workflow", "json")
            
            return Response(
                content=json_bytes,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}.json"}
            )
            
        except Exception as e:
            app_logger.error(
                "Full JSON export failed",
                export_type="json",
                thread_id=request.thread_id,
                error=str(e)
            )
            raise HTTPException(status_code=500, detail=f"Failed to export full workflow as JSON: {str(e)}")


@router.get("/export/formats")
async def get_export_formats():
    """Get available export formats."""
    return {
        "success": True,
        "data": {
            "formats": [
                {
                    "type": "pdf",
                    "name": "PRD PDF Document",
                    "description": "Professional PDF document with product requirements",
                    "endpoint": "/api/v1/export/prd/pdf"
                },
                {
                    "type": "csv",
                    "name": "Jira-Compatible CSV",
                    "description": "CSV file formatted for import into Jira",
                    "endpoint": "/api/v1/export/tickets/csv"
                },
                {
                    "type": "json",
                    "name": "Complete Workflow JSON",
                    "description": "Full workflow data in JSON format",
                    "endpoint": "/api/v1/export/full/json"
                }
            ]
        }
    }
