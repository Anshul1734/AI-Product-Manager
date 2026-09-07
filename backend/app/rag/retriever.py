"""
Retrieval orchestration: query -> hybrid search -> cited context block.

The assembled context carries `[S1]`-style markers and a matching citation list
so agents can attribute claims and the UI can show which knowledge grounded
each artifact.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Sequence

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..schemas.artifacts import Citation
from .embeddings import EmbeddingProvider, get_embedding_provider
from .store import HybridStore, ScoredChunk


@dataclass
class RetrievalResult:
    query: str
    chunks: List[ScoredChunk]
    context: str
    citations: List[Citation]
    retrievers_used: List[str]

    @property
    def is_empty(self) -> bool:
        return not self.chunks


@lru_cache(maxsize=1)
def get_store() -> HybridStore:
    """Load the committed index once per process."""
    store = HybridStore.load(settings.RAG_INDEX_PATH)
    if store.size == 0:
        app_logger.warning(
            "Knowledge index is empty or missing; agents will run without retrieval grounding",
            path=str(settings.RAG_INDEX_PATH),
        )
    else:
        app_logger.info(
            "Knowledge index loaded",
            chunks=store.size,
            dense_enabled=store.has_dense,
            provider=store.embedding_provider_name,
        )
    return store


class Retriever:
    """Hybrid retriever over the product-management knowledge base."""

    def __init__(self, store: Optional[HybridStore] = None, provider: Optional[EmbeddingProvider] = None):
        self.store = store if store is not None else get_store()
        self._provider = provider

    @property
    def provider(self) -> EmbeddingProvider:
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    @property
    def available(self) -> bool:
        return settings.RAG_ENABLED and self.store.size > 0

    async def retrieve(
        self,
        query: str,
        *,
        k: Optional[int] = None,
        domains: Optional[Sequence[str]] = None,
        authorities: Optional[Sequence[str]] = None,
    ) -> RetrievalResult:
        if not self.available or not query.strip():
            return RetrievalResult(query, [], "", [], [])

        limit = k or settings.RAG_TOP_K
        candidates = settings.RAG_CANDIDATES_PER_RETRIEVER
        allowed = self.store.filter_indices(domains, authorities)

        lexical = self.store.search_lexical(query, candidates, allowed)

        dense: List[tuple[int, float]] = []
        retrievers = ["bm25"] if lexical else []
        if self.store.has_dense and self.provider.enabled:
            try:
                vectors = await self.provider.embed([query], is_query=True)
                if vectors:
                    dense = self.store.search_dense(vectors[0], candidates, allowed)
                    if dense:
                        retrievers.append("dense")
            except Exception as exc:
                # Dense retrieval is an enhancement; a provider outage must not
                # take down the pipeline, it just degrades recall.
                app_logger.warning("Dense retrieval unavailable, using BM25 only", error=str(exc)[:200])

        fused = self.store.fuse(
            lexical,
            dense,
            rrf_k=settings.RAG_RRF_K,
            limit=limit,
            max_per_doc=settings.RAG_MAX_CHUNKS_PER_DOC,
        )
        context, citations = self.assemble(fused)
        return RetrievalResult(query, fused, context, citations, retrievers)

    @staticmethod
    def assemble(chunks: Sequence[ScoredChunk]) -> tuple[str, List[Citation]]:
        """Render retrieved chunks as a cited context block."""
        if not chunks:
            return "", []

        blocks: List[str] = []
        citations: List[Citation] = []
        budget = settings.RAG_MAX_CONTEXT_CHARS

        for position, scored in enumerate(chunks, start=1):
            marker = f"S{position}"
            chunk = scored.chunk
            block = (
                f"[{marker}] {chunk.title} — {chunk.heading}\n{chunk.text}"
            )
            if len(block) > budget:
                if budget < 400:
                    break
                block = block[:budget].rsplit("\n", 1)[0] + "\n…"
            budget -= len(block)
            blocks.append(block)
            citations.append(
                Citation(
                    marker=marker,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    heading=chunk.heading,
                    score=round(scored.score, 5),
                )
            )

        return "\n\n---\n\n".join(blocks), citations
