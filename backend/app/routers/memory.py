"""Memory inspection and management."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from ..core.config.settings import settings
from ..memory.store import get_memory

router = APIRouter(prefix="/memory", tags=["memory"])


def _require_memory():
    if not settings.MEMORY_ENABLED:
        raise HTTPException(status_code=503, detail="Memory is disabled (MEMORY_ENABLED=false)")
    return get_memory()


@router.get("/stats")
async def stats() -> Dict[str, Any]:
    memory = _require_memory()
    return {"success": True, "data": memory.stats()}


@router.get("/search")
async def search(
    query: str = Query(..., min_length=2, max_length=500),
    k: int = Query(3, ge=1, le=10),
) -> Dict[str, Any]:
    """BM25 recall over previously generated plans."""
    memory = _require_memory()
    matches = memory.search(query, k=k)
    return {
        "success": True,
        "data": {
            "query": query,
            "matches": [
                {"relevance": score, **entry.to_dict()}
                for entry, score in matches
            ],
        },
    }


@router.get("/threads/{thread_id}")
async def thread_history(thread_id: str, limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    memory = _require_memory()
    entries = memory.thread_history(thread_id, limit=limit)
    return {
        "success": True,
        "data": {
            "thread_id": thread_id,
            "total": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        },
    }


@router.delete("")
async def clear() -> Dict[str, Any]:
    memory = _require_memory()
    removed = memory.clear()
    return {"success": True, "message": f"Cleared {removed} entr{'y' if removed == 1 else 'ies'}"}
