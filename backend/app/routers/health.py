"""
Health check router for the AI Product Manager API.
"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core import app_logger, settings


router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        health_data = {
            "status": "healthy",
            "message": "AI Product Manager is running",
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "api": "active",
                "llm": "Groq",
                "export_service": "active"
            }
        }
        
        app_logger.info("Health check completed", status="healthy")
        
        return health_data
        
    except Exception as e:
        app_logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "message": "AI Product Manager Agent API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "workflow": "/api/v1/generate",
            "export": "/api/v1/export",
            "health": "/api/v1/health"
        }
    }
