"""
Retrieval orchestration: query -> hybrid search -> cited context block.

The assembled context carries `[S1]`-style markers and a matching citation list
so agents can attribute claims and the UI can show which knowledge grounded
each artifact.

Two pools feed one context block:

- the curated product-management corpus (committed index, in memory), and
- the caller's uploaded documents (Qdrant, scoped to a workspace).

Each pool gets its own passage count and character budget rather than
competing in one ranking. RRF scores from separate fusions are not comparable,
and the pools answer different questions: the corpus says how to do product
work well, the uploads say what is true about *this* product. A plan needs
both, so neither is allowed to crowd the other out.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..core.observability import traceable, without
from ..schemas.artifacts import Citation
from .embeddings import EmbeddingProvider, get_embedding_provider
from .store import HybridStore, ScoredChunk
from .uploads import UploadedDocuments, get_uploaded_documents

#: Prefix on uploaded passages in the context block. Agents are told what it
#: means in their prompt, so keep the two in step (see agents/base.py).
UPLOAD_LABEL = "Uploaded document"


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

    @property
    def uploaded_count(self) -> int:
        return sum(1 for scored in self.chunks if scored.chunk.source == "upload")


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


def _trace_passages(result: "RetrievalResult") -> List[Dict[str, Any]]:
    return [
        {
            "type": "Document",
            "page_content": scored.chunk.text,
            "metadata": {
                "marker": citation.marker,
                "source": scored.chunk.source,
                "title": scored.chunk.title,
                "heading": scored.chunk.heading,
                "rrf_score": round(scored.score, 5),
                "matched_by": scored.retrievers,
            },
        }
        for scored, citation in zip(result.chunks, result.citations)
    ]


class Retriever:
    """Hybrid retriever over the curated corpus and a workspace's uploads."""

    def __init__(
        self,
        store: Optional[HybridStore] = None,
        provider: Optional[EmbeddingProvider] = None,
        uploads: Optional[UploadedDocuments] = None,
    ):
        self.store = store if store is not None else get_store()
        self._provider = provider
        self._uploads = uploads

    @property
    def provider(self) -> EmbeddingProvider:
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    @property
    def uploads(self) -> Optional[UploadedDocuments]:
        if not settings.uploads_configured:
            return None
        if self._uploads is None:
            self._uploads = get_uploaded_documents()
        return self._uploads

    @property
    def available(self) -> bool:
        return settings.RAG_ENABLED and (self.store.size > 0 or settings.uploads_configured)

    @traceable(run_type="retriever", name="retrieve", process_inputs=without(), process_outputs=_trace_passages)
    async def retrieve(
        self,
        query: str,
        *,
        k: Optional[int] = None,
        domains: Optional[Sequence[str]] = None,
        authorities: Optional[Sequence[str]] = None,
        workspace_id: Optional[str] = None,
        upload_query: Optional[str] = None,
        upload_k: Optional[int] = None,
    ) -> RetrievalResult:
        """Search both pools.

        `domains`/`authorities` filter the curated corpus only; uploads carry
        no such taxonomy. `upload_query` lets a caller phrase the uploads
        search differently -- the corpus wants "best practice for X", a user's
        own notes want the idea itself.
        """
        if not settings.RAG_ENABLED or not query.strip():
            return RetrievalResult(query, [], "", [], [])

        uploads = self.uploads if workspace_id else None
        if uploads is not None:
            try:
                if await uploads.passage_count(workspace_id) == 0:
                    uploads = None
            except Exception as exc:
                app_logger.warning("Uploaded-document retrieval failed", error=str(exc)[:200])
                uploads = None
        retrievers: List[str] = []

        # Embed each distinct query text once, in a single provider call.
        wanted: Dict[str, str] = {}
        if self.store.has_dense:
            wanted["curated"] = query
        if uploads is not None:
            wanted["uploads"] = upload_query or query
        vectors: Dict[str, List[float]] = {}
        if wanted and self.provider.enabled:
            texts = list(dict.fromkeys(wanted.values()))
            try:
                vectors = dict(zip(texts, await self.provider.embed(texts, is_query=True)))
            except Exception as exc:
                # Dense retrieval is an enhancement; a provider outage must not
                # take down the pipeline, it just degrades recall.
                app_logger.warning("Dense retrieval unavailable, using BM25 only", error=str(exc)[:200])

        uploaded: List[ScoredChunk] = []
        if uploads is not None:
            try:
                uploaded = await uploads.search(
                    workspace_id,
                    wanted["uploads"],
                    vectors.get(wanted["uploads"]),
                    upload_k or settings.RAG_UPLOAD_TOP_K,
                )
            except Exception as exc:
                app_logger.warning("Uploaded-document retrieval failed", error=str(exc)[:200])
            if uploaded:
                retrievers.append("uploads")

        curated: List[ScoredChunk] = []
        if self.store.size > 0:
            candidates = settings.RAG_CANDIDATES_PER_RETRIEVER
            allowed = self.store.filter_indices(domains, authorities)
            lexical = self.store.search_lexical(query, candidates, allowed)
            if lexical:
                retrievers.insert(0, "bm25")

            dense: List[tuple[int, float]] = []
            if vectors.get(query):
                dense = self.store.search_dense(vectors[query], candidates, allowed)
            if dense:
                retrievers.insert(1 if lexical else 0, "dense")

            curated = self.store.fuse(
                lexical,
                dense,
                rrf_k=settings.RAG_RRF_K,
                limit=k or settings.RAG_TOP_K,
                max_per_doc=settings.RAG_MAX_CHUNKS_PER_DOC,
            )

        kept, context, citations = self.assemble(curated, uploaded=uploaded)
        return RetrievalResult(query, kept, context, citations, retrievers)

    @staticmethod
    def assemble(
        chunks: Sequence[ScoredChunk], *, uploaded: Sequence[ScoredChunk] = ()
    ) -> Tuple[List[ScoredChunk], str, List[Citation]]:
        """Render retrieved chunks as a cited context block.

        Uploaded passages come first and are labelled as the user's own
        material. Returns the chunks that fit the budgets alongside the text, so
        callers pairing chunks with citations never fall out of step.
        """
        kept: List[ScoredChunk] = []
        blocks: List[str] = []
        citations: List[Citation] = []

        def render(pool: Sequence[ScoredChunk], budget: int) -> None:
            for scored in pool:
                chunk = scored.chunk
                marker = f"S{len(citations) + 1}"
                prefix = f"{UPLOAD_LABEL}: " if chunk.source == "upload" else ""
                block = f"[{marker}] {prefix}{chunk.title} — {chunk.heading}\n{chunk.text}"
                if len(block) > budget:
                    if budget < 400:
                        break
                    block = block[:budget].rsplit("\n", 1)[0] + "\n…"
                budget -= len(block)
                kept.append(scored)
                blocks.append(block)
                citations.append(
                    Citation(
                        marker=marker,
                        doc_id=chunk.doc_id,
                        title=chunk.title,
                        heading=chunk.heading,
                        score=round(scored.score, 5),
                        source=chunk.source,
                    )
                )

        render(uploaded, settings.RAG_UPLOAD_CONTEXT_CHARS)
        render(chunks, settings.RAG_MAX_CONTEXT_CHARS)
        return kept, "\n\n---\n\n".join(blocks), citations
