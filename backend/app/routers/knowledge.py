"""
Knowledge-base endpoints.

Exposing retrieval directly makes the RAG layer inspectable: you can see which
passages a query actually returns, and which retriever found them, without
running a full pipeline.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..rag.retriever import Retriever
from ..schemas.requests import KnowledgeSearchRequest
from ..schemas.responses import KnowledgeSearchResponse

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
async def list_documents() -> Dict[str, Any]:
    """List the indexed corpus."""
    retriever = Retriever()
    store = retriever.store
    return {
        "success": True,
        "data": {
            "documents": store.documents(),
            "domains": store.domains,
            "chunk_count": store.size,
            "dense_enabled": store.has_dense,
            "embedding_provider": store.embedding_provider_name,
        },
    }


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search(request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    """Run a hybrid retrieval query and return the ranked passages."""
    retriever = Retriever()
    if not retriever.available:
        raise HTTPException(
            status_code=503,
            detail="Knowledge index is not loaded. Build it with: python -m app.rag.ingest",
        )

    result = await retriever.retrieve(
        request.query,
        k=request.k,
        domains=[request.domain] if request.domain else None,
    )

    return KnowledgeSearchResponse(
        success=True,
        query=request.query,
        retrievers=result.retrievers_used,
        message=f"{len(result.chunks)} passage(s) matched",
        results=[
            {
                "marker": citation.marker,
                "doc_id": scored.chunk.doc_id,
                "title": scored.chunk.title,
                "heading": scored.chunk.heading,
                "domain": scored.chunk.domain,
                "authority": scored.chunk.authority,
                "text": scored.chunk.text,
                "fused_score": round(scored.score, 5),
                "matched_by": scored.retrievers,
                "lexical_rank": scored.lexical_rank,
                "dense_rank": scored.dense_rank,
            }
            for scored, citation in zip(result.chunks, result.citations)
        ],
    )
