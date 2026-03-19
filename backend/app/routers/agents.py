"""
Advanced agent management router for the AI Product Manager API.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..core import app_logger, request_context

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint."""
    return {
        "success": True,
        "message": "Agent router is working",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/capabilities")
async def get_agent_capabilities():
    """Get capabilities of all registered agents."""
    try:
        # Import here to avoid circular imports
        from ..services import WorkflowService
        workflow_service = WorkflowService()
        
        capabilities = workflow_service.get_agent_capabilities()
        
        return {
            "success": True,
            "data": capabilities,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        app_logger.error("Failed to get agent capabilities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent capabilities")


@router.get("/performance")
async def get_agent_performance():
    """Get performance metrics for all agents."""
    try:
        from ..services import WorkflowService
        workflow_service = WorkflowService()
        
        performance = workflow_service.get_agent_performance()
        
        return {
            "success": True,
            "data": performance
        }
        
    except Exception as e:
        app_logger.error("Failed to get agent performance", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent performance")


@router.post("/reset-metrics")
async def reset_agent_metrics(agent_name: Optional[str] = None):
    """Reset metrics for specific agent or all agents."""
    try:
        from ..services import WorkflowService
        workflow_service = WorkflowService()
        
        await workflow_service.reset_agent_metrics(agent_name)
        
        return {
            "success": True,
            "message": f"Metrics reset for {agent_name if agent_name else 'all agents'}"
        }
        
    except Exception as e:
        app_logger.error("Failed to reset agent metrics", agent_name=agent_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reset agent metrics")


@router.get("/system-status")
async def get_agent_system_status():
    """Get comprehensive agent system status."""
    try:
        from ..services import WorkflowService
        workflow_service = WorkflowService()
        
        status = workflow_service.get_system_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        app_logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")
