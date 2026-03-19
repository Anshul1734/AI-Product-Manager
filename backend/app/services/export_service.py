"""
Export service for generating downloadable files.
"""
import io
import json
import csv
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from ..core import app_logger, settings, ExportError
from ..schemas.requests import ExportRequest


class ExportService:
    """Service for handling export operations."""
    
    def __init__(self):
        self.logger = app_logger
    
    async def export_prd_pdf(self, request: ExportRequest) -> bytes:
        """Export PRD as PDF document."""
        try:
            self.logger.info(
                f"Starting PRD PDF export",
                thread_id=request.thread_id,
                export_type=request.export_type
            )
            
            # Generate workflow data
            workflow_state = await self.workflow_service.execute_workflow(
                request.idea, 
                request.thread_id
            )
            
            # Create PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                name='CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                name='CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.darkblue
            )
            
            content = []
            
            # Title
            content.append(Paragraph("Product Requirements Document", title_style))
            content.append(Spacer(1, 12))
            
            # Product Info
            plan = workflow_state.plan
            content.append(Paragraph("Product Overview", heading_style))
            content.append(Paragraph(f"<b>Product Name:</b> {plan.product_name}", styles['Normal']))
            content.append(Paragraph(f"<b>Problem Statement:</b> {plan.problem_statement}", styles['Normal']))
            content.append(Spacer(1, 12))
            
            # Target Users
            content.append(Paragraph("Target Users", heading_style))
            for user in plan.target_users:
                content.append(Paragraph(f"• {user}", styles['Normal']))
            content.append(Spacer(1, 12))
            
            # Core Goals
            content.append(Paragraph("Core Goals", heading_style))
            for goal in plan.core_goals:
                content.append(Paragraph(f"• {goal}", styles['Normal']))
            content.append(Spacer(1, 12))
            
            # PRD Data
            prd = workflow_state.prd
            content.append(Paragraph("User Personas", heading_style))
            for persona in prd.user_personas:
                content.append(Paragraph(f"<b>{persona.name}</b>", styles['Normal']))
                content.append(Paragraph(persona.description, styles['Normal']))
                content.append(Paragraph("<b>Pain Points:</b>", styles['Normal']))
                for point in persona.pain_points:
                    content.append(Paragraph(f"  - {point}", styles['Normal']))
                content.append(Spacer(1, 12))
            
            # User Stories
            content.append(Paragraph("User Stories", heading_style))
            for story in prd.user_stories:
                content.append(Paragraph(f"<b>{story.title}</b>", styles['Normal']))
                content.append(Paragraph(
                    f"As a <b>{story.as_a}</b>, I want to <b>{story.i_want_to}</b> so that <b>{story.so_that}</b>", 
                    styles['Normal']
                ))
                content.append(Spacer(1, 12))
            
            # Success Metrics
            content.append(Paragraph("Success Metrics", heading_style))
            for metric in prd.success_metrics:
                content.append(Paragraph(f"<b>{metric.name}</b>", styles['Normal']))
                content.append(Paragraph(metric.description, styles['Normal']))
                content.append(Paragraph(f"<b>Target:</b> {metric.target}", styles['Normal']))
                content.append(Spacer(1, 12))
            
            # Build PDF
            doc.build(content)
            pdf_buffer.seek(0)
            
            pdf_bytes = pdf_buffer.getvalue()
            
            self.logger.info(
                f"PRD PDF export completed successfully",
                file_size=len(pdf_bytes),
                thread_id=request.thread_id
            )
            
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(
                f"PRD PDF export failed",
                error=str(e),
                thread_id=request.thread_id
            )
            raise ExportError(
                f"Failed to export PRD as PDF: {str(e)}",
                error_code="PDF_EXPORT_FAILED",
                details={"thread_id": request.thread_id, "error": str(e)}
            )
    
    async def export_tickets_csv(self, request: ExportRequest) -> bytes:
        """Export tickets as Jira-compatible CSV."""
        try:
            self.logger.info(
                f"Starting tickets CSV export",
                thread_id=request.thread_id,
                export_type=request.export_type
            )
            
            # Generate workflow data
            workflow_state = await self.workflow_service.execute_workflow(
                request.idea, 
                request.thread_id
            )
            
            # Create CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            
            # CSV Headers (Jira-compatible)
            headers = [
                'Issue Type', 'Summary', 'Description', 'Priority', 'Status', 
                'Epic Link', 'Story Points', 'Assignee', 'Reporter'
            ]
            writer.writerow(headers)
            
            # Write tickets
            tickets = workflow_state.tickets
            for epic in tickets.epics:
                epic_name = epic.epic_name
                
                # Write epic
                writer.writerow([
                    'Epic', 
                    epic_name, 
                    epic.description, 
                    'High', 
                    'To Do', 
                    '', 
                    '', 
                    '', 
                    'AI Product Manager'
                ])
                
                # Write stories
                for story in epic.stories:
                    writer.writerow([
                        'Story',
                        story.story_title,
                        story.description,
                        'Medium',
                        'To Do',
                        epic_name,
                        story.story_points or '',
                        '',
                        'AI Product Manager'
                    ])
                    
                    # Write tasks
                    for task in story.tasks:
                        writer.writerow([
                            'Task',
                            task.title,
                            f"Estimated time: {task.estimated_hours or 'N/A'} hours",
                            'Low',
                            'To Do',
                            epic_name,
                            '',
                            '',
                            'AI Product Manager'
                        ])
            
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            self.logger.info(
                f"Tickets CSV export completed successfully",
                file_size=len(csv_bytes),
                thread_id=request.thread_id
            )
            
            return csv_bytes
            
        except Exception as e:
            self.logger.error(
                f"Tickets CSV export failed",
                error=str(e),
                thread_id=request.thread_id
            )
            raise ExportError(
                f"Failed to export tickets as CSV: {str(e)}",
                error_code="CSV_EXPORT_FAILED",
                details={"thread_id": request.thread_id, "error": str(e)}
            )
    
    async def export_full_json(self, request: ExportRequest) -> bytes:
        """Export complete workflow as JSON."""
        try:
            self.logger.info(
                f"Starting full JSON export",
                thread_id=request.thread_id,
                export_type=request.export_type
            )
            
            # Generate workflow data
            workflow_state = await self.workflow_service.execute_workflow(
                request.idea, 
                request.thread_id
            )
            
            # Add metadata
            export_data = {
                'export_metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'product_idea': request.idea,
                    'thread_id': request.thread_id,
                    'export_version': '1.0',
                    'export_type': 'full_workflow'
                },
                'workflow_data': workflow_state.dict()
            }
            
            json_bytes = json.dumps(export_data, indent=2, default=str).encode('utf-8')
            
            self.logger.info(
                f"Full JSON export completed successfully",
                file_size=len(json_bytes),
                thread_id=request.thread_id
            )
            
            return json_bytes
            
        except Exception as e:
            self.logger.error(
                f"Full JSON export failed",
                error=str(e),
                thread_id=request.thread_id
            )
            raise ExportError(
                f"Failed to export full workflow as JSON: {str(e)}",
                error_code="JSON_EXPORT_FAILED",
                details={"thread_id": request.thread_id, "error": str(e)}
            )
    
    def generate_filename(self, product_name: str, export_type: str) -> str:
        """Generate filename for export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        sanitized_name = product_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        return f"{export_type}_{sanitized_name}_{timestamp}"
    
    def get_content_type(self, export_type: str) -> str:
        """Get content type for export."""
        content_types = {
            'pdf': 'application/pdf',
            'csv': 'text/csv',
            'json': 'application/json'
        }
        return content_types.get(export_type, 'application/octet-stream')
