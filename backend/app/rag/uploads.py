"""
User-uploaded documents: parse, chunk, embed, store in Qdrant, retrieve.

Uploads are scoped to a *workspace* -- an opaque id the client generates and
sends with every request -- so one visitor's documents never ground another
visitor's plan. There are no user accounts, so a workspace id is a bearer
token, not an access control: anyone holding it can read that workspace.

Retrieval over uploads is hybrid, like the curated corpus:

- **Dense** search runs in Qdrant, filtered to the workspace.
- **Lexical** BM25 runs in-process over that workspace's chunks, fetched from
  Qdrant once and cached. Exact terms -- a product name, a customer, an error
  code -- are what users' own documents are full of, and embeddings blur them.

The two ranked lists are fused with the same RRF as the curated store.

Qdrant is reached over its REST API with httpx rather than through
`qdrant-client`: the official client costs ~110 MB of resident memory on import
(generated pydantic models, grpc, numpy), which matters on a 512 MB instance,
and this module needs only six endpoints.
"""
from __future__ import annotations

import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from .chunking import Chunk, chunk_sections
from .embeddings import EmbeddingProvider, get_embedding_provider
from .parsers import UnsupportedDocument, extract_sections
from .store import HybridStore, ScoredChunk

WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,64}$")

#: Stable namespace for point ids: Qdrant accepts only integers or UUIDs.
_POINT_NAMESPACE = uuid.UUID("5b0f8a7e-3f43-4f8e-9a51-2d1c2f6a9b10")

#: Payload fields that are filtered on. Qdrant Cloud's strict mode rejects
#: filters on unindexed fields, so each gets a keyword index at creation.
_INDEXED_FIELDS = ("workspace_id", "doc_id", "sha256")

_DOC_FIELDS = ["doc_id", "title", "filename", "uploaded_at", "size_bytes", "doc_chars", "chunk_count"]
_CHUNK_FIELDS = ["chunk_id", "doc_id", "title", "heading", "text"]

_UPSERT_BATCH = 64
_SCROLL_PAGE = 256

#: Lexical indexes per workspace. Invalidated on every write from this process;
#: the TTL bounds staleness when another instance wrote.
_LEXICAL_TTL_SECONDS = 300.0
_LEXICAL_MAX_WORKSPACES = 128
_lexical_cache: Dict[str, Tuple[float, HybridStore, Dict[str, int]]] = {}


class UploadError(RuntimeError):
    """An upload operation failed in a way the caller should see."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def validate_workspace(workspace_id: Optional[str]) -> str:
    value = (workspace_id or "").strip()
    if not WORKSPACE_PATTERN.match(value):
        raise UploadError("workspace_id must be 6-64 characters of letters, digits, '-' or '_'.", 422)
    return value


def _match(workspace_id: str, **fields: str) -> Dict[str, Any]:
    return {
        "must": [
            {"key": key, "match": {"value": value}}
            for key, value in {"workspace_id": workspace_id, **fields}.items()
        ]
    }


class QdrantStore:
    """Minimal async client for the Qdrant REST endpoints this module needs."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection: Optional[str] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.url = (url or settings.QDRANT_URL or "").strip().rstrip("/")
        self.api_key = (api_key or settings.QDRANT_API_KEY or "").strip()
        self.collection = collection or settings.QDRANT_COLLECTION
        self.timeout = timeout or settings.QDRANT_TIMEOUT_SECONDS
        self._ready_dimensions: Optional[int] = None
        #: Test seam: an httpx transport standing in for the network.
        self._transport = transport

    async def _request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None, *, allow_404: bool = False
    ) -> Optional[Dict[str, Any]]:
        headers = {"api-key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                response = await client.request(method, f"{self.url}{path}", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise UploadError(f"Vector database unreachable: {type(exc).__name__}", 502) from exc

        if response.status_code == 404 and allow_404:
            return None
        if response.status_code >= 400:
            detail = response.text[:300]
            try:
                detail = response.json().get("status", {}).get("error") or detail
            except ValueError:
                pass
            status = 502 if response.status_code in (401, 403) or response.status_code >= 500 else 400
            raise UploadError(f"Vector database error ({response.status_code}): {detail}", status)
        return response.json()

    def _path(self, suffix: str = "") -> str:
        return f"/collections/{self.collection}{suffix}"

    async def ensure_collection(self, dimensions: int) -> None:
        """Create the collection on first use; refuse a dimension mismatch."""
        if self._ready_dimensions == dimensions:
            return

        info = await self._request("GET", self._path(), allow_404=True)
        if info is None:
            try:
                await self._request(
                    "PUT",
                    self._path(),
                    {"vectors": {"size": dimensions, "distance": "Cosine"}},
                )
            except UploadError as exc:
                # A concurrent first upload created it between our GET and PUT.
                if "already exists" not in str(exc):
                    raise
            for field in _INDEXED_FIELDS:
                await self._request(
                    "PUT",
                    self._path("/index?wait=true"),
                    {"field_name": field, "field_schema": "keyword"},
                )
            app_logger.info("Created Qdrant collection", collection=self.collection, dimensions=dimensions)
        else:
            vectors = ((info.get("result") or {}).get("config") or {}).get("params", {}).get("vectors") or {}
            existing = vectors.get("size")
            if existing and existing != dimensions:
                raise UploadError(
                    f"Collection '{self.collection}' holds {existing}-dimensional vectors but the current "
                    f"embedding provider produces {dimensions}. Point QDRANT_COLLECTION at a new collection "
                    "after changing embedding provider or model.",
                    409,
                )
        self._ready_dimensions = dimensions

    async def upsert(self, points: List[Dict[str, Any]]) -> None:
        for start in range(0, len(points), _UPSERT_BATCH):
            await self._request(
                "PUT", self._path("/points?wait=true"), {"points": points[start : start + _UPSERT_BATCH]}
            )

    async def query(self, vector: Sequence[float], workspace_id: str, limit: int) -> List[Dict[str, Any]]:
        data = await self._request(
            "POST",
            self._path("/points/query"),
            {
                "query": list(vector),
                "filter": _match(workspace_id),
                "limit": limit,
                "with_payload": ["chunk_id"],
            },
            allow_404=True,
        )
        return ((data or {}).get("result") or {}).get("points") or []

    async def scroll(
        self, workspace_id: str, fields: List[str], *, max_points: int = 50_000, **match: str
    ) -> List[Dict[str, Any]]:
        """Every point in a workspace (optionally narrowed by `match`), payload only."""
        points: List[Dict[str, Any]] = []
        offset: Any = None
        while len(points) < max_points:
            body: Dict[str, Any] = {
                "filter": _match(workspace_id, **match),
                "limit": min(_SCROLL_PAGE, max_points - len(points)),
                "with_payload": fields,
                "with_vector": False,
            }
            if offset is not None:
                body["offset"] = offset
            data = await self._request("POST", self._path("/points/scroll"), body, allow_404=True)
            result = (data or {}).get("result") or {}
            points.extend(result.get("points") or [])
            offset = result.get("next_page_offset")
            if offset is None:
                break
        return points

    async def delete(self, workspace_id: str, **match: str) -> None:
        await self._request(
            "POST",
            self._path("/points/delete?wait=true"),
            {"filter": _match(workspace_id, **match)},
            allow_404=True,
        )

    async def ping(self) -> None:
        await self._request("GET", "/collections")


class UploadedDocuments:
    """The upload lifecycle and retrieval over one workspace's documents."""

    def __init__(self, store: Optional[QdrantStore] = None, provider: Optional[EmbeddingProvider] = None):
        self.store = store or QdrantStore()
        self._provider = provider

    @property
    def provider(self) -> EmbeddingProvider:
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    @staticmethod
    def require_configured() -> None:
        reason = settings.uploads_unavailable_reason()
        if reason:
            raise UploadError(reason, 503)

    # -------------------------------------------------------------- writes

    async def add(self, workspace_id: str, filename: str, data: bytes) -> Dict[str, Any]:
        self.require_configured()
        workspace_id = validate_workspace(workspace_id)
        filename = PurePath((filename or "document").replace("\\", "/")).name[:200] or "document"

        if not data:
            raise UploadError("The file is empty.")
        if len(data) > settings.UPLOAD_MAX_BYTES:
            raise UploadError(
                f"File is {len(data) / 1_048_576:.1f} MB; the limit is "
                f"{settings.UPLOAD_MAX_BYTES / 1_048_576:.0f} MB.",
                413,
            )

        sha256 = hashlib.sha256(data).hexdigest()
        duplicate = await self.store.scroll(workspace_id, _DOC_FIELDS, max_points=1, sha256=sha256)
        if duplicate:
            return {**_document_summary(duplicate[0].get("payload") or {}), "duplicate": True}

        existing = await self.list(workspace_id)
        if len(existing) >= settings.UPLOAD_MAX_DOCUMENTS:
            raise UploadError(
                f"This workspace already holds {len(existing)} documents (limit "
                f"{settings.UPLOAD_MAX_DOCUMENTS}). Delete one before adding more.",
                409,
            )

        try:
            sections = extract_sections(filename, data)
        except UnsupportedDocument as exc:
            raise UploadError(str(exc), 415) from exc

        doc_id = f"up_{uuid.uuid4().hex[:12]}"
        title = PurePath(filename).stem.strip() or filename
        chunks = chunk_sections(
            sections,
            doc_id=doc_id,
            title=title,
            max_chars=settings.UPLOAD_CHUNK_CHARS,
            overlap=settings.UPLOAD_CHUNK_OVERLAP,
        )
        if not chunks:
            raise UploadError("No readable text found in this file.")
        if len(chunks) > settings.UPLOAD_MAX_CHUNKS:
            raise UploadError(
                f"This document splits into {len(chunks)} passages; the limit is "
                f"{settings.UPLOAD_MAX_CHUNKS}. Upload a shorter document or split it.",
                413,
            )

        try:
            vectors = await self.provider.embed([chunk.embedding_text for chunk in chunks])
        except Exception as exc:
            raise UploadError(f"Embedding failed: {str(exc)[:200]}", 502) from exc
        if len(vectors) != len(chunks):
            raise UploadError(f"Embedding provider returned {len(vectors)} vectors for {len(chunks)} passages", 502)

        await self.store.ensure_collection(len(vectors[0]))

        doc_chars = sum(len(text) for _, text in sections)
        document = {
            "doc_id": doc_id,
            "title": title,
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(data),
            "doc_chars": doc_chars,
            "chunk_count": len(chunks),
        }
        points = [
            {
                "id": str(uuid.uuid5(_POINT_NAMESPACE, f"{workspace_id}:{chunk.id}")),
                "vector": vector,
                "payload": {
                    **document,
                    "workspace_id": workspace_id,
                    "sha256": sha256,
                    "chunk_id": chunk.id,
                    "heading": chunk.heading,
                    "text": chunk.text,
                    "embedding_provider": self.provider.name,
                },
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        try:
            await self.store.upsert(points)
        except UploadError:
            # Leave no half-written document behind.
            await self.store.delete(workspace_id, doc_id=doc_id)
            raise
        finally:
            invalidate(workspace_id)

        app_logger.info(
            "Document uploaded", workspace=workspace_id[:8], doc_id=doc_id, chunks=len(chunks), chars=doc_chars
        )
        return {**document, "duplicate": False}

    async def remove(self, workspace_id: str, doc_id: str) -> None:
        self.require_configured()
        workspace_id = validate_workspace(workspace_id)
        found = await self.store.scroll(workspace_id, ["doc_id"], max_points=1, doc_id=doc_id)
        if not found:
            raise UploadError("Document not found in this workspace.", 404)
        await self.store.delete(workspace_id, doc_id=doc_id)
        invalidate(workspace_id)

    # --------------------------------------------------------------- reads

    async def list(self, workspace_id: str) -> List[Dict[str, Any]]:
        self.require_configured()
        workspace_id = validate_workspace(workspace_id)
        documents: Dict[str, Dict[str, Any]] = {}
        for point in await self.store.scroll(workspace_id, _DOC_FIELDS):
            payload = point.get("payload") or {}
            doc_id = payload.get("doc_id")
            if doc_id and doc_id not in documents:
                documents[doc_id] = _document_summary(payload)
        return sorted(documents.values(), key=lambda item: item["uploaded_at"], reverse=True)

    async def passage_count(self, workspace_id: str) -> int:
        """Passages in a workspace, from the cache. Lets callers skip
        embedding a query for a workspace with nothing in it."""
        corpus, _ = await self._lexical_index(workspace_id)
        return corpus.size

    async def search(
        self,
        workspace_id: str,
        query: str,
        query_vector: Optional[Sequence[float]],
        limit: int,
    ) -> List[ScoredChunk]:
        """Hybrid BM25 + dense retrieval over one workspace, fused with RRF."""
        corpus, positions = await self._lexical_index(workspace_id)
        if corpus.size == 0:
            return []

        candidates = settings.RAG_CANDIDATES_PER_RETRIEVER
        lexical = corpus.search_lexical(query, candidates)

        dense: List[Tuple[int, float]] = []
        if query_vector:
            for hit in await self.store.query(query_vector, workspace_id, candidates):
                position = positions.get((hit.get("payload") or {}).get("chunk_id"))
                # A hit missing from the cache was written by another instance
                # since the cache was built; it surfaces after the TTL.
                if position is not None:
                    dense.append((position, float(hit.get("score") or 0.0)))

        return corpus.fuse(lexical, dense, rrf_k=settings.RAG_RRF_K, limit=limit, max_per_doc=limit)

    async def _lexical_index(self, workspace_id: str) -> Tuple[HybridStore, Dict[str, int]]:
        cached = _lexical_cache.get(workspace_id)
        if cached and time.monotonic() - cached[0] < _LEXICAL_TTL_SECONDS:
            return cached[1], cached[2]

        chunks = [
            Chunk(
                id=payload["chunk_id"],
                doc_id=payload.get("doc_id", ""),
                title=payload.get("title", ""),
                heading=payload.get("heading", ""),
                text=payload.get("text", ""),
                domain="uploaded",
                authority="user",
                source="upload",
            )
            for payload in (
                point.get("payload") or {} for point in await self.store.scroll(workspace_id, _CHUNK_FIELDS)
            )
            if payload.get("chunk_id")
        ]
        chunks.sort(key=lambda chunk: chunk.id)
        corpus = HybridStore(chunks)
        positions = {chunk.id: index for index, chunk in enumerate(chunks)}

        if len(_lexical_cache) >= _LEXICAL_MAX_WORKSPACES:
            oldest = min(_lexical_cache, key=lambda key: _lexical_cache[key][0])
            _lexical_cache.pop(oldest, None)
        _lexical_cache[workspace_id] = (time.monotonic(), corpus, positions)
        return corpus, positions


def invalidate(workspace_id: str) -> None:
    _lexical_cache.pop(workspace_id, None)


def _document_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {field: payload.get(field) for field in _DOC_FIELDS}


_documents: Optional[UploadedDocuments] = None


def get_uploaded_documents() -> UploadedDocuments:
    global _documents
    if _documents is None:
        _documents = UploadedDocuments()
    return _documents
