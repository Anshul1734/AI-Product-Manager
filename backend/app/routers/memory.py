"""
Memory management router for the AI Product Manager API.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..core import app_logger
from ..agents import create_memory_manager
from ..core.observability import create_metrics_collector, create_tracing_service


router = APIRouter()

# Global instances (in production, these would be dependency injected)
memory_manager = create_memory_manager(
    create_metrics_collector(),
    create_tracing_service()
)


class ConversationTurnRequest(BaseModel):
    """Request model for adding conversation turn."""
    thread_id: str
    user_input: str
    agent_response: str
    agent_name: str
    metadata: Optional[Dict[str, Any]] = None


class AgentStateRequest(BaseModel):
    """Request model for storing agent state."""
    agent_name: str
    state_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class AgentLearningRequest(BaseModel):
    """Request model for storing agent learning."""
    agent_name: str
    learning_type: str
    learning_data: Dict[str, Any]
    confidence: float
    source: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/memory/conversation/add")
async def add_conversation_turn(request: ConversationTurnRequest):
    """Add a conversation turn to memory."""
    try:
        turn_id = await memory_manager.add_conversation_turn(
            thread_id=request.thread_id,
            user_input=request.user_input,
            agent_response=request.agent_response,
            agent_name=request.agent_name,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "turn_id": turn_id,
            "message": "Conversation turn added successfully"
        }
        
    except Exception as e:
        app_logger.error("Failed to add conversation turn", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add conversation turn")


@router.get("/memory/context/{agent_name}")
async def get_agent_context(
    agent_name: str,
    thread_id: str = Query(...),
    query: str = Query(...),
    max_conversation_turns: int = Query(3),
    max_agent_learning: int = Query(2),
    similarity_threshold: float = Query(0.6)
):
    """Get context for an agent."""
    try:
        context = await memory_manager.get_context_for_agent(
            thread_id=thread_id,
            agent_name=agent_name,
            query=query,
            max_conversation_turns=max_conversation_turns,
            max_agent_learning=max_agent_learning,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "success": True,
            "data": context
        }
        
    except Exception as e:
        app_logger.error("Failed to get agent context", agent_name=agent_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get agent context")


@router.post("/memory/agent/state")
async def store_agent_state(request: AgentStateRequest):
    """Store agent state."""
    try:
        state_id = await memory_manager.store_agent_state(
            agent_name=request.agent_name,
            state_data=request.state_data,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "state_id": state_id,
            "message": "Agent state stored successfully"
        }
        
    except Exception as e:
        app_logger.error("Failed to store agent state", agent_name=request.agent_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to store agent state")


@router.post("/memory/agent/learning")
async def store_agent_learning(request: AgentLearningRequest):
    """Store agent learning."""
    try:
        learning_id = await memory_manager.store_agent_learning(
            agent_name=request.agent_name,
            learning_type=request.learning_type,
            learning_data=request.learning_data,
            confidence=request.confidence,
            source=request.source,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "learning_id": learning_id,
            "message": "Agent learning stored successfully"
        }
        
    except Exception as e:
        app_logger.error("Failed to store agent learning", agent_name=request.agent_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to store agent learning")


@router.get("/memory/search")
async def search_memory(
    query: str = Query(...),
    thread_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    memory_types: Optional[str] = Query(None),
    max_results: int = Query(20)
):
    """Search across memory systems."""
    try:
        memory_types_list = memory_types.split(",") if memory_types else None
        
        results = await memory_manager.search_memory(
            query=query,
            thread_id=thread_id,
            agent_name=agent_name,
            memory_types=memory_types_list,
            max_results=max_results
        )
        
        return {
            "success": True,
            "data": results,
            "query": query,
            "filters": {
                "thread_id": thread_id,
                "agent_name": agent_name,
                "memory_types": memory_types_list
            }
        }
        
    except Exception as e:
        app_logger.error("Failed to search memory", query=query, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search memory")


@router.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics."""
    try:
        stats = await memory_manager.get_memory_stats()
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        app_logger.error("Failed to get memory stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get memory statistics")


@router.post("/memory/cleanup")
async def cleanup_memory():
    """Clean up old memory entries."""
    try:
        result = await memory_manager.cleanup_old_memory()
        
        return {
            "success": True,
            "data": result,
            "message": "Memory cleanup completed"
        }
        
    except Exception as e:
        app_logger.error("Failed to cleanup memory", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cleanup memory")


@router.delete("/memory/clear")
async def clear_memory(
    thread_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None)
):
    """Clear memory entries."""
    try:
        cleared_counts = await memory_manager.clear_memory(
            thread_id=thread_id,
            agent_name=agent_name,
            memory_type=memory_type
        )
        
        return {
            "success": True,
            "data": cleared_counts,
            "message": "Memory cleared successfully"
        }
        
    except Exception as e:
        app_logger.error("Failed to clear memory", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear memory")


@router.get("/memory/export")
async def export_memory(
    thread_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    format: str = Query("json")
):
    """Export memory data."""
    try:
        export_data = await memory_manager.export_memory(
            thread_id=thread_id,
            agent_name=agent_name,
            format=format
        )
        
        return {
            "success": True,
            "data": export_data,
            "format": format
        }
        
    except Exception as e:
        app_logger.error("Failed to export memory", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export memory")


@router.get("/memory/health")
async def get_memory_health():
    """Get memory system health status."""
    try:
        health_status = memory_manager.get_health_status()
        
        return {
            "success": True,
            "data": health_status
        }
        
    except Exception as e:
        app_logger.error("Failed to get memory health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get memory health status")
