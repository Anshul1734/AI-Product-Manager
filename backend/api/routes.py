import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Iterator, List
from orchestrator import WorkflowManager
from schemas import WorkflowOutput, WorkflowState
from .websocket import manager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["product-manager"])

# Initialize workflow manager with LangGraph (default)
workflow_manager = WorkflowManager(use_langgraph=True)

# Security
security = HTTPBearer(auto_error=False)

# Simple API key validation (in production, use proper auth)
VALID_API_KEYS = {"demo-api-key-123", "test-key-456"}


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for protected endpoints"""
    if credentials and credentials.credentials in VALID_API_KEYS:
        return credentials.credentials
    return None  # Allow access without key for demo purposes


class BatchRequest(BaseModel):
    """Request model for batch processing"""
    product_ideas: List[str] = Field(..., min_items=1, max_items=5, description="List of product ideas to process")
    thread_id: Optional[str] = Field(None, description="Thread ID for batch processing")
    use_legacy: Optional[bool] = Field(False, description="Use legacy sequential execution")


class BatchResponse(BaseModel):
    """Response model for batch processing"""
    success: bool
    results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    total_execution_time: Optional[float] = None
    processed_count: int = 0
    failed_count: int = 0


class AnalyticsResponse(BaseModel):
    """Response model for analytics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_execution_time: float = 0.0
    most_common_steps: Dict[str, int] = Field(default_factory=dict)
    active_threads: int = 0


# Simple in-memory analytics (in production, use proper analytics)
analytics_data = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "execution_times": [],
    "step_counts": {},
    "active_threads": set()
}


class ProductIdeaRequest(BaseModel):
    """Request model for product idea"""
    idea: str = Field(..., min_length=10, description="Product idea description")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation memory")
    use_legacy: Optional[bool] = Field(False, description="Use legacy sequential execution instead of LangGraph")


class WorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    success: bool
    data: Optional[WorkflowOutput] = None
    state: Optional[WorkflowState] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    thread_id: Optional[str] = None


class StreamResponse(BaseModel):
    """Response model for streaming workflow"""
    event: str
    data: Dict[str, Any]
    step: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    workflow_engine: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy", 
        message="AI Product Manager Agent is running",
        workflow_engine="LangGraph" if workflow_manager.use_langgraph else "Legacy"
    )


@router.post("/generate", response_model=WorkflowResponse)
async def generate_product_plan(
    request: ProductIdeaRequest,
    background_tasks: BackgroundTasks,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Generate complete product plan including vision, PRD, architecture, and tickets
    
    Args:
        request: Product idea request
        background_tasks: FastAPI background tasks
        
    Returns:
        WorkflowResponse: Complete workflow results
    """
    import time
    start_time = time.time()
    
    # Update analytics
    analytics_data["total_requests"] += 1
    if request.thread_id:
        analytics_data["active_threads"].add(request.thread_id)
    
    try:
        logger.info(f"Starting workflow generation for product idea: {request.idea[:100]}...")
        
        # Configure workflow manager based on request
        if request.use_legacy and workflow_manager.use_langgraph:
            # Create legacy manager for this request
            manager = WorkflowManager(use_langgraph=False)
        elif not request.use_legacy and not workflow_manager.use_langgraph:
            # Create LangGraph manager for this request
            manager = WorkflowManager(use_langgraph=True)
        else:
            manager = workflow_manager
        
        # Execute workflow
        result = manager.execute_workflow(request.idea, request.thread_id)
        
        execution_time = time.time() - start_time
        logger.info(f"Workflow completed in {execution_time:.2f} seconds")
        
        # Update analytics
        analytics_data["successful_requests"] += 1
        analytics_data["execution_times"].append(execution_time)
        
        # Update step counts
        if hasattr(result, 'plan') and result.plan:
            analytics_data["step_counts"]["planner"] = analytics_data["step_counts"].get("planner", 0) + 1
        if hasattr(result, 'prd') and result.prd:
            analytics_data["step_counts"]["analyst"] = analytics_data["step_counts"].get("analyst", 0) + 1
        if hasattr(result, 'architecture') and result.architecture:
            analytics_data["step_counts"]["architect"] = analytics_data["step_counts"].get("architect", 0) + 1
        if hasattr(result, 'tickets') and result.tickets:
            analytics_data["step_counts"]["ticket_generator"] = analytics_data["step_counts"].get("ticket_generator", 0) + 1
        
        return WorkflowResponse(
            success=True,
            data=result,
            execution_time=execution_time,
            thread_id=request.thread_id
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        execution_time = time.time() - start_time
        analytics_data["failed_requests"] += 1
        return WorkflowResponse(
            success=False,
            error=f"Validation error: {str(e)}",
            execution_time=execution_time
        )
        
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        execution_time = time.time() - start_time
        analytics_data["failed_requests"] += 1
        return WorkflowResponse(
            success=False,
            error=f"Runtime error: {str(e)}",
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        execution_time = time.time() - start_time
        analytics_data["failed_requests"] += 1
        return WorkflowResponse(
            success=False,
            error=f"Unexpected error: {str(e)}",
            execution_time=execution_time
        )
    finally:
        # Clean up active threads
        if request.thread_id:
            analytics_data["active_threads"].discard(request.thread_id)


@router.post("/generate/stream")
async def generate_product_plan_stream(request: ProductIdeaRequest):
    """
    Stream workflow execution step by step (LangGraph only)
    
    Args:
        request: Product idea request
        
    Returns:
        StreamingResponse: Step-by-step workflow results
    """
    from fastapi.responses import StreamingResponse
    import json
    
    if request.use_legacy:
        raise HTTPException(
            status_code=400, 
            detail="Streaming is only available with LangGraph workflow engine"
        )
    
    async def generate_stream():
        try:
            for event in workflow_manager.stream_workflow(request.product_idea, request.thread_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {
                "error": str(e),
                "step": "stream_error"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/generate/async")
async def generate_product_plan_async(request: ProductIdeaRequest):
    """
    Async endpoint for product plan generation (returns task ID)
    
    Args:
        request: Product idea request
        
    Returns:
        Dict: Task ID for checking status
    """
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # In a real implementation, you'd use a task queue like Celery
    # For now, we'll just return the task ID
    return {"task_id": task_id, "message": "Task started"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of async task
    
    Args:
        task_id: Task identifier
        
    Returns:
        Dict: Task status
    """
    # In a real implementation, you'd check the task queue
    return {"task_id": task_id, "status": "completed", "progress": 100}


@router.get("/state/{thread_id}")
async def get_workflow_state(thread_id: str):
    """
    Get current workflow state for a thread (LangGraph only)
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Dict: Current workflow state
    """
    try:
        state = workflow_manager.get_workflow_state(thread_id)
        
        if state is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return {
            "thread_id": thread_id,
            "state": state.model_dump(),
            "exists": True
        }
        
    except NotImplementedError:
        raise HTTPException(
            status_code=400, 
            detail="State management is only available with LangGraph workflow engine"
        )
    except Exception as e:
        logger.error(f"Failed to get workflow state: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow state")


@router.post("/validate")
async def validate_product_idea(request: ProductIdeaRequest):
    """
    Validate product idea before processing
    
    Args:
        request: Product idea request
        
    Returns:
        Dict: Validation results
    """
    issues = []
    
    if len(request.product_idea) < 20:
        issues.append("Product idea is too short")
    
    if len(request.product_idea) > 2000:
        issues.append("Product idea is too long")
    
    # Check for basic content
    if not any(word in request.product_idea.lower() for word in ['app', 'platform', 'system', 'tool', 'service']):
        issues.append("Product idea should specify the type of product")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "suggestions": [
            "Be more specific about the problem you're solving",
            "Include target users or market",
            "Describe key features or benefits"
        ] if issues else []
    }


@router.post("/batch", response_model=BatchResponse)
async def batch_generate_product_plans(
    request: BatchRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Process multiple product ideas in batch
    
    Args:
        request: Batch request with multiple product ideas
        api_key: Optional API key for authentication
        
    Returns:
        BatchResponse: Results for all product ideas
    """
    import time
    start_time = time.time()
    
    results = []
    errors = []
    processed_count = 0
    failed_count = 0
    
    logger.info(f"Starting batch processing for {len(request.product_ideas)} product ideas")
    
    # Configure workflow manager
    manager = WorkflowManager(use_langgraph=not request.use_legacy)
    
    for i, product_idea in enumerate(request.product_ideas):
        try:
            logger.info(f"Processing item {i+1}/{len(request.product_ideas)}: {product_idea[:50]}...")
            
            # Execute workflow for each idea
            result = manager.execute_workflow(
                product_idea, 
                thread_id=f"{request.thread_id}_batch_{i}" if request.thread_id else f"batch_{i}"
            )
            
            results.append({
                "index": i,
                "product_idea": product_idea,
                "success": True,
                "data": result.model_dump()
            })
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Item {i+1} failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            failed_count += 1
            
            results.append({
                "index": i,
                "product_idea": product_idea,
                "success": False,
                "error": str(e)
            })
    
    total_execution_time = time.time() - start_time
    
    logger.info(f"Batch processing completed: {processed_count} successful, {failed_count} failed in {total_execution_time:.2f}s")
    
    return BatchResponse(
        success=failed_count == 0,
        results=results,
        errors=errors,
        total_execution_time=total_execution_time,
        processed_count=processed_count,
        failed_count=failed_count
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(api_key: Optional[str] = Depends(verify_api_key)):
    """
    Get system analytics and usage statistics
    
    Args:
        api_key: Optional API key for authentication
        
    Returns:
        AnalyticsResponse: System analytics
    """
    # Calculate average execution time
    avg_time = 0.0
    if analytics_data["execution_times"]:
        avg_time = sum(analytics_data["execution_times"]) / len(analytics_data["execution_times"])
    
    return AnalyticsResponse(
        total_requests=analytics_data["total_requests"],
        successful_requests=analytics_data["successful_requests"],
        failed_requests=analytics_data["failed_requests"],
        average_execution_time=avg_time,
        most_common_steps=analytics_data["step_counts"],
        active_threads=len(analytics_data["active_threads"])
    )


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time workflow updates
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
    """
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "execute_workflow":
                product_idea = message.get("idea")
                thread_id = message.get("thread_id")
                
                if product_idea:
                    # Execute workflow and stream results
                    await manager.execute_workflow_stream(client_id, product_idea, thread_id)
                else:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "Missing idea in request"
                    })
            elif message.get("type") == "ping":
                await manager.send_message(client_id, {
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                })
            else:
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {str(e)}")
        manager.disconnect(client_id)


@router.post("/reset-analytics")
async def reset_analytics(api_key: Optional[str] = Depends(verify_api_key)):
    """
    Reset analytics data (admin only)
    
    Args:
        api_key: API key for authentication
        
    Returns:
        Dict: Reset confirmation
    """
    global analytics_data
    
    analytics_data = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "execution_times": [],
        "step_counts": {},
        "active_threads": set()
    }
    
    logger.info("Analytics data reset")
    
    return {
        "message": "Analytics data reset successfully",
        "timestamp": time.time()
    }


@router.get("/threads")
async def list_active_threads(api_key: Optional[str] = Depends(verify_api_key)):
    """
    List all active threads
    
    Args:
        api_key: Optional API key for authentication
        
    Returns:
        Dict: Active threads information
    """
    active_threads = list(analytics_data["active_threads"])
    
    return {
        "active_threads": active_threads,
        "count": len(active_threads),
        "timestamp": time.time()
    }
