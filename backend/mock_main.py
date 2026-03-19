import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time
import random
import json
import csv
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Product Manager Agent",
    description="Mock API for testing frontend integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ProductIdeaRequest(BaseModel):
    idea: str
    thread_id: Optional[str] = None
    use_legacy: Optional[bool] = False

# Mock response data
def generate_mock_response(idea: str) -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "plan": {
                "product_name": f"AI-Powered {idea.split()[0].title()} Platform",
                "problem_statement": f"Addressing the challenges in {idea[:50]}...",
                "target_users": ["Developers", "Product Managers", "Business Analysts"],
                "core_goals": ["Streamline workflow", "Increase productivity", "Reduce costs"],
                "key_features_high_level": ["AI-driven insights", "Real-time collaboration", "Automated reporting"]
            },
            "prd": {
                "problem_statement": f"The current approach to {idea[:50]} is inefficient and time-consuming.",
                "target_users": ["Enterprise teams", "Small businesses", "Individual professionals"],
                "user_personas": [
                    {
                        "name": "Alex Chen",
                        "description": "Senior product manager looking to streamline workflow",
                        "pain_points": ["Manual processes", "Limited visibility", "Poor communication"]
                    }
                ],
                "user_stories": [
                    {
                        "title": "Generate Product Plan",
                        "as_a": "product manager",
                        "i_want_to": "generate comprehensive product plans",
                        "so_that": "I can accelerate product development"
                    }
                ],
                "success_metrics": [
                    {
                        "name": "Time to Market",
                        "description": "Reduce product development time by 50%",
                        "target": "6 months"
                    }
                ]
            },
            "architecture": {
                "system_design": "Microservices architecture with AI/ML integration",
                "tech_stack": {
                    "frontend": "React with TypeScript",
                    "backend": "FastAPI with Python",
                    "database": "PostgreSQL with Redis cache",
                    "infrastructure": "Docker containers on AWS"
                },
                "architecture_components": [
                    "API Gateway",
                    "Authentication Service",
                    "AI Processing Engine",
                    "Database Layer",
                    "Notification Service"
                ],
                "api_endpoints": [
                    {
                        "name": "Generate Product Plan",
                        "method": "POST",
                        "endpoint": "/api/v1/generate",
                        "description": "Generate comprehensive product plan"
                    }
                ],
                "database_schema": [
                    {
                        "table_name": "product_plans",
                        "fields": [
                            {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY"},
                            {"name": "idea", "type": "TEXT", "constraints": "NOT NULL"},
                            {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"}
                        ]
                    }
                ]
            },
            "tickets": {
                "epics": [
                    {
                        "epic_name": "Core Product Planning",
                        "description": "Implement the main product planning functionality",
                        "stories": [
                            {
                                "story_title": "User Input Processing",
                                "description": "Process and validate user product ideas",
                                "acceptance_criteria": [
                                    "User can input product idea",
                                    "System validates input format",
                                    "Error messages are clear"
                                ],
                                "tasks": [
                                    {
                                        "title": "Create input form",
                                        "description": "Design and implement the input form",
                                        "estimated_hours": "8"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        },
        "execution_time": round(random.uniform(2.5, 5.0), 2),
        "thread_id": f"thread_{int(time.time())}"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Product Manager Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    health_id = f"health_{int(time.time())}"
    
    logger.info(f"[{health_id}] 💓 HEALTH CHECK")
    logger.info(f"[{health_id}]   - Status: Checking system health")
    logger.info(f"[{health_id}]   - Engine: Mock")
    logger.info(f"[{health_id}]   - Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    health_status = {
        "status": "healthy",
        "message": "AI Product Manager Agent is running",
        "workflow_engine": "Mock",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "uptime": "Running"
    }
    
    logger.info(f"[{health_id}] ✅ HEALTH CHECK COMPLETED")
    logger.info(f"[{health_id}]   - Response: {health_status['status']}")
    
    return health_status

@app.post("/api/v1/generate")
async def generate_product_plan(request: ProductIdeaRequest):
    """Generate product plan endpoint"""
    request_id = f"req_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # Log incoming request
    logger.info(f"[{request_id}] === NEW REQUEST RECEIVED ===")
    logger.info(f"[{request_id}] Request Details:")
    logger.info(f"[{request_id}]   - Idea: {request.idea[:100]}{'...' if len(request.idea) > 100 else ''}")
    logger.info(f"[{request_id}]   - Thread ID: {request.thread_id}")
    logger.info(f"[{request_id}]   - Use Legacy: {request.use_legacy}")
    logger.info(f"[{request_id}] Starting pipeline execution...")
    
    try:
        # Step 1: Planner Agent
        logger.info(f"[{request_id}] 🤖 STEP 1: PLANNER AGENT")
        start_time = time.time()
        
        # Simulate planner processing
        await asyncio.sleep(0.5)
        plan_result = {
            "product_name": f"AI-Powered {request.idea.split()[0].title()} Platform",
            "problem_statement": f"Addressing the challenges in {request.idea[:50]}...",
            "target_users": ["Developers", "Product Managers", "Business Analysts"],
            "core_goals": ["Streamline workflow", "Increase productivity", "Reduce costs"],
            "key_features_high_level": ["AI-driven insights", "Real-time collaboration", "Automated reporting"]
        }
        
        planner_time = time.time() - start_time
        logger.info(f"[{request_id}]   ✅ Planner completed in {planner_time:.2f}s")
        logger.info(f"[{request_id}]   📋 Generated: {plan_result['product_name']}")
        logger.info(f"[{request_id}]   🎯 Problem: {plan_result['problem_statement'][:80]}...")
        
        # Step 2: Analyst Agent
        logger.info(f"[{request_id}] 🤖 STEP 2: ANALYST AGENT")
        start_time = time.time()
        
        # Simulate analyst processing
        await asyncio.sleep(0.6)
        prd_result = {
            "problem_statement": f"The current approach to {request.idea[:50]} is inefficient and time-consuming.",
            "target_users": ["Enterprise teams", "Small businesses", "Individual professionals"],
            "user_personas": [
                {
                    "name": "Alex Chen",
                    "description": "Senior product manager looking to streamline workflow",
                    "pain_points": ["Manual processes", "Limited visibility", "Poor communication"]
                }
            ],
            "user_stories": [
                {
                    "title": "Generate Product Plan",
                    "as_a": "product manager",
                    "i_want_to": "generate comprehensive product plans",
                    "so_that": "I can accelerate product development"
                }
            ],
            "success_metrics": [
                {
                    "name": "Time to Market",
                    "description": "Reduce product development time by 50%",
                    "target": "6 months"
                }
            ]
        }
        
        analyst_time = time.time() - start_time
        logger.info(f"[{request_id}]   ✅ Analyst completed in {analyst_time:.2f}s")
        logger.info(f"[{request_id}]   👥 Target Users: {len(prd_result['target_users'])} groups")
        logger.info(f"[{request_id}]   📝 User Stories: {len(prd_result['user_stories'])} stories")
        logger.info(f"[{request_id}]   📊 Success Metrics: {len(prd_result['success_metrics'])} metrics")
        
        # Step 3: Architect Agent
        logger.info(f"[{request_id}] 🤖 STEP 3: ARCHITECT AGENT")
        start_time = time.time()
        
        # Simulate architect processing
        await asyncio.sleep(0.7)
        architecture_result = {
            "system_design": "Microservices architecture with AI/ML integration",
            "tech_stack": {
                "frontend": "React with TypeScript",
                "backend": "FastAPI with Python",
                "database": "PostgreSQL with Redis cache",
                "infrastructure": "Docker containers on AWS"
            },
            "architecture_components": [
                "API Gateway",
                "Authentication Service",
                "AI Processing Engine",
                "Database Layer",
                "Notification Service"
            ],
            "api_endpoints": [
                {
                    "name": "Generate Product Plan",
                    "method": "POST",
                    "endpoint": "/api/v1/generate",
                    "description": "Generate comprehensive product plan"
                }
            ],
            "database_schema": [
                {
                    "table_name": "product_plans",
                    "fields": [
                        {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY"},
                        {"name": "idea", "type": "TEXT", "constraints": "NOT NULL"},
                        {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"}
                    ]
                }
            ]
        }
        
        architect_time = time.time() - start_time
        logger.info(f"[{request_id}]   ✅ Architect completed in {architect_time:.2f}s")
        logger.info(f"[{request_id}]   🏗️  Architecture: {architecture_result['system_design']}")
        logger.info(f"[{request_id}]   🔧 Tech Stack: {', '.join(architecture_result['tech_stack'].keys())}")
        logger.info(f"[{request_id}]   📦 Components: {len(architecture_result['architecture_components'])} services")
        
        # Step 4: Ticket Generator Agent
        logger.info(f"[{request_id}] 🤖 STEP 4: TICKET GENERATOR AGENT")
        start_time = time.time()
        
        # Simulate ticket generator processing
        await asyncio.sleep(0.8)
        tickets_result = {
            "epics": [
                {
                    "epic_name": "Core Product Planning",
                    "description": "Implement the main product planning functionality",
                    "stories": [
                        {
                            "story_title": "User Input Processing",
                            "description": "Process and validate user product ideas",
                            "acceptance_criteria": [
                                "User can input product idea",
                                "System validates input format",
                                "Error messages are clear"
                            ],
                            "tasks": [
                                {
                                    "title": "Create input form",
                                    "description": "Design and implement the input form",
                                    "estimated_hours": "8"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        ticket_time = time.time() - start_time
        logger.info(f"[{request_id}]   ✅ Ticket Generator completed in {ticket_time:.2f}s")
        logger.info(f"[{request_id}]   📋 Epics: {len(tickets_result['epics'])}")
        total_stories = sum(len(epic['stories']) for epic in tickets_result['epics'])
        logger.info(f"[{request_id}]   📝 Stories: {total_stories}")
        total_tasks = sum(len(story['tasks']) for epic in tickets_result['epics'] for story in epic['stories'])
        logger.info(f"[{request_id}]   ✅ Tasks: {total_tasks}")
        
        # Generate final response
        logger.info(f"[{request_id}] 🔄 GENERATING FINAL RESPONSE")
        response = {
            "success": True,
            "data": {
                "plan": plan_result,
                "prd": prd_result,
                "architecture": architecture_result,
                "tickets": tickets_result
            },
            "execution_time": round(planner_time + analyst_time + architect_time + ticket_time, 2),
            "thread_id": request.thread_id or f"thread_{int(time.time())}"
        }
        
        # Log final response summary
        logger.info(f"[{request_id}] ✅ PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"[{request_id}] 📊 EXECUTION SUMMARY:")
        logger.info(f"[{request_id}]   - Total Time: {response['execution_time']}s")
        logger.info(f"[{request_id}]   - Planner: {planner_time:.2f}s")
        logger.info(f"[{request_id}]   - Analyst: {analyst_time:.2f}s")
        logger.info(f"[{request_id}]   - Architect: {architect_time:.2f}s")
        logger.info(f"[{request_id}]   - Ticket Generator: {ticket_time:.2f}s")
        logger.info(f"[{request_id}]   - Thread ID: {response['thread_id']}")
        logger.info(f"[{request_id}] 🎉 RESPONSE READY FOR CLIENT")
        
        return response
        
    except Exception as e:
        logger.error(f"[{request_id}] ❌ PIPELINE FAILED")
        logger.error(f"[{request_id}]   Error Type: {type(e).__name__}")
        logger.error(f"[{request_id}]   Error Message: {str(e)}")
        logger.error(f"[{request_id}]   Error Details: {repr(e)}")
        
        # Return error response
        error_response = {
            "success": False,
            "error": f"Pipeline failed: {str(e)}",
            "execution_time": 0.0,
            "thread_id": request.thread_id
        }
        
        logger.error(f"[{request_id}] 🚨 ERROR RESPONSE SENT TO CLIENT")
        return error_response

@app.post("/api/v1/validate")
async def validate_product_idea(request: ProductIdeaRequest):
    """Validate product idea endpoint"""
    request_id = f"val_{int(time.time())}_{random.randint(1000, 9999)}"
    
    logger.info(f"[{request_id}] 🔍 VALIDATION REQUEST")
    logger.info(f"[{request_id}]   - Idea: {request.idea[:100]}{'...' if len(request.idea) > 100 else ''}")
    logger.info(f"[{request_id}]   - Thread ID: {request.thread_id}")
    
    try:
        issues = []
        
        if len(request.idea) < 10:
            issues.append("Idea is too short - please provide more detail")
        
        if not any(keyword in request.idea.lower() for keyword in ['problem', 'solve', 'help', 'improve']):
            issues.append("Consider describing the problem you're solving")
        
        validation_result = {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": [
                "Be more specific about the problem you're solving",
                "Include target users or market",
                "Describe key features or benefits"
            ] if issues else []
        }
        
        logger.info(f"[{request_id}] ✅ VALIDATION COMPLETED")
        logger.info(f"[{request_id}]   - Valid: {validation_result['valid']}")
        logger.info(f"[{request_id}]   - Issues Found: {len(issues)}")
        logger.info(f"[{request_id}]   - Suggestions: {len(validation_result['suggestions'])}")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"[{request_id}] ❌ VALIDATION FAILED")
        logger.error(f"[{request_id}]   Error: {str(e)}")
        
        return {
            "valid": False,
            "issues": [f"Validation error: {str(e)}"],
            "suggestions": []
        }

# Export endpoints
@app.post("/api/v1/export/prd/pdf")
async def export_prd_pdf(request: ProductIdeaRequest):
    """Export PRD as downloadable PDF"""
    try:
        request_id = f"export_prd_{int(time.time())}"
        logger.info(f"[{request_id}] 📄 STARTING PRD PDF EXPORT")
        
        # Generate mock workflow data
        workflow_data = generate_mock_workflow_data(request.idea)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
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
        plan = workflow_data['plan']
        content.append(Paragraph("Product Overview", heading_style))
        content.append(Paragraph(f"<b>Product Name:</b> {plan['product_name']}", styles['Normal']))
        content.append(Paragraph(f"<b>Problem Statement:</b> {plan['problem_statement']}", styles['Normal']))
        content.append(Spacer(1, 12))
        
        # Target Users
        content.append(Paragraph("Target Users", heading_style))
        for user in plan['target_users']:
            content.append(Paragraph(f"• {user}", styles['Normal']))
        content.append(Spacer(1, 12))
        
        # Core Goals
        content.append(Paragraph("Core Goals", heading_style))
        for goal in plan['core_goals']:
            content.append(Paragraph(f"• {goal}", styles['Normal']))
        content.append(Spacer(1, 12))
        
        # PRD Data
        prd = workflow_data['prd']
        content.append(Paragraph("User Personas", heading_style))
        for persona in prd['user_personas']:
            content.append(Paragraph(f"<b>{persona['name']}</b>", styles['Normal']))
            content.append(Paragraph(persona['description'], styles['Normal']))
            content.append(Paragraph("<b>Pain Points:</b>", styles['Normal']))
            for point in persona['pain_points']:
                content.append(Paragraph(f"  - {point}", styles['Normal']))
            content.append(Spacer(1, 12))
        
        # User Stories
        content.append(Paragraph("User Stories", heading_style))
        for story in prd['user_stories']:
            content.append(Paragraph(f"<b>{story['title']}</b>", styles['Normal']))
            content.append(Paragraph(
                f"As a <b>{story['as_a']}</b>, I want to <b>{story['i_want_to']}</b> so that <b>{story['so_that']}</b>", 
                styles['Normal']
            ))
            content.append(Spacer(1, 12))
        
        # Success Metrics
        content.append(Paragraph("Success Metrics", heading_style))
        for metric in prd['success_metrics']:
            content.append(Paragraph(f"<b>{metric['name']}</b>", styles['Normal']))
            content.append(Paragraph(metric['description'], styles['Normal']))
            content.append(Paragraph(f"<b>Target:</b> {metric['target']}", styles['Normal']))
            content.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(content)
        buffer.seek(0)
        
        logger.info(f"[{request_id}] ✅ PRD PDF EXPORT COMPLETED")
        
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=PRD_{plan['product_name'].replace(' ', '_')}.pdf"}
        )
        
    except Exception as e:
        logger.error(f"PRD PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/v1/export/tickets/csv")
async def export_tickets_csv(request: ProductIdeaRequest):
    """Export tickets as Jira-compatible CSV"""
    try:
        request_id = f"export_tickets_{int(time.time())}"
        logger.info(f"[{request_id}] 📊 STARTING TICKETS CSV EXPORT")
        
        # Generate mock workflow data
        workflow_data = generate_mock_workflow_data(request.idea)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV Headers (Jira-compatible)
        headers = [
            'Issue Type', 'Summary', 'Description', 'Priority', 'Status', 
            'Epic Link', 'Story Points', 'Assignee', 'Reporter'
        ]
        writer.writerow(headers)
        
        # Write tickets
        tickets = workflow_data['tickets']
        for epic in tickets['epics']:
            epic_name = epic['epic_name']
            
            # Write epic
            writer.writerow([
                'Epic', 
                epic_name, 
                epic['description'], 
                'High', 
                'To Do', 
                '', 
                '', 
                '', 
                'AI Product Manager'
            ])
            
            # Write stories
            for story in epic['stories']:
                writer.writerow([
                    'Story',
                    story['story_title'],
                    story['description'],
                    'Medium',
                    'To Do',
                    epic_name,
                    '',  # Story points could be estimated
                    '',
                    'AI Product Manager'
                ])
                
                # Write tasks
                for task in story['tasks']:
                    writer.writerow([
                        'Task',
                        task['title'],
                        f"Estimated time: {task.get('estimated_hours', 'N/A')} hours",
                        'Low',
                        'To Do',
                        epic_name,
                        '',
                        '',
                        'AI Product Manager'
                    ])
        
        logger.info(f"[{request_id}] ✅ TICKETS CSV EXPORT COMPLETED")
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=tickets_{workflow_data['plan']['product_name'].replace(' ', '_')}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Tickets CSV export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/v1/export/full/json")
async def export_full_json(request: ProductIdeaRequest):
    """Export complete workflow as JSON"""
    try:
        request_id = f"export_full_{int(time.time())}"
        logger.info(f"[{request_id}] 📋 STARTING FULL JSON EXPORT")
        
        # Generate mock workflow data
        workflow_data = generate_mock_workflow_data(request.idea)
        
        # Add metadata
        export_data = {
            'export_metadata': {
                'timestamp': time.time(),
                'product_idea': request.idea,
                'thread_id': request.thread_id,
                'export_version': '1.0'
            },
            'workflow_data': workflow_data
        }
        
        logger.info(f"[{request_id}] ✅ FULL JSON EXPORT COMPLETED")
        
        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=workflow_{workflow_data['plan']['product_name'].replace(' ', '_')}.json"}
        )
        
    except Exception as e:
        logger.error(f"Full JSON export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# Add asyncio import
import asyncio

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "mock_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
