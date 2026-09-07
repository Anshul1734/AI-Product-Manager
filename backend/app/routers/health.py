"""Health and readiness."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Response

from ..core.config.settings import settings
from ..memory.store import get_memory
from ..rag.retriever import get_store

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(response: Response) -> Dict[str, Any]:
    """Report component readiness.

    Returns 503 when the LLM is unconfigured: without it the service cannot do
    its job, and a green health check would hide that from a deploy pipeline.
    """
    store = get_store()
    llm_ready = settings.llm_configured

    components: Dict[str, Any] = {
        "llm": {
            "ready": llm_ready,
            "provider": "groq",
            "model": settings.GROQ_MODEL,
            "fast_model": settings.GROQ_FAST_MODEL,
            "detail": None if llm_ready else "GROQ_API_KEY is not set",
        },
        "retrieval": {
            "ready": store.size > 0,
            "corpus_chunks": store.size,
            "documents": len(store.documents()),
            "dense": store.has_dense,
            "provider": store.embedding_provider_name,
            "detail": None if store.size else "knowledge index missing; run python -m app.rag.ingest",
        },
        "memory": {
            "ready": settings.MEMORY_ENABLED,
            **({"stats": get_memory().stats()} if settings.MEMORY_ENABLED else {}),
        },
    }

    healthy = llm_ready
    if not healthy:
        response.status_code = 503

    return {
        "status": "healthy" if healthy else "degraded",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "serverless": settings.is_serverless,
        "components": components,
    }


@router.get("/")
async def index() -> Dict[str, Any]:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "generate": f"{settings.API_V1_STR}/generate",
            "generate_stream": f"{settings.API_V1_STR}/generate/stream",
            "validate": f"{settings.API_V1_STR}/validate",
            "pipeline": f"{settings.API_V1_STR}/pipeline",
            "knowledge_search": f"{settings.API_V1_STR}/knowledge/search",
            "health": f"{settings.API_V1_STR}/health",
        },
    }
