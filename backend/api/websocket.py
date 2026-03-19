import logging
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from orchestrator import WorkflowManager


logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time workflow updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.workflow_manager = WorkflowManager(use_langgraph=True)
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
        
        # Send welcome message
        await self.send_message(client_id, {
            "type": "connection",
            "message": "Connected to AI Product Manager Agent",
            "client_id": client_id
        })
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {str(e)}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {str(e)}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def execute_workflow_stream(self, client_id: str, product_idea: str, thread_id: Optional[str] = None):
        """Execute workflow and stream results to WebSocket client"""
        try:
            # Send start message
            await self.send_message(client_id, {
                "type": "workflow_started",
                "product_idea": product_idea,
                "thread_id": thread_id
            })
            
            # Stream workflow execution
            for event in self.workflow_manager.stream_workflow(product_idea, thread_id):
                await self.send_message(client_id, {
                    "type": "workflow_step",
                    "event": event,
                    "timestamp": asyncio.get_event_loop().time()
                })
            
            # Get final state
            final_state = self.workflow_manager.get_workflow_state(thread_id) if thread_id else None
            
            # Send completion message
            await self.send_message(client_id, {
                "type": "workflow_completed",
                "state": final_state.model_dump() if final_state else None,
                "timestamp": asyncio.get_event_loop().time()
            })
            
        except Exception as e:
            logger.error(f"Workflow execution failed for {client_id}: {str(e)}")
            await self.send_message(client_id, {
                "type": "workflow_error",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            })


# Global connection manager
manager = ConnectionManager()
