"""Retrieval-augmented generation over a curated product-management corpus."""

from .chunking import Chunk, chunk_markdown, load_knowledge_dir
from .retriever import RetrievalResult, Retriever, get_store
from .store import HybridStore, ScoredChunk

__all__ = [
    "Chunk",
    "chunk_markdown",
    "load_knowledge_dir",
    "HybridStore",
    "ScoredChunk",
    "Retriever",
    "RetrievalResult",
    "get_store",
]
