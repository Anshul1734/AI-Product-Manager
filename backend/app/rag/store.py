"""
Hybrid vector store: BM25 lexical retrieval fused with dense cosine retrieval
via Reciprocal Rank Fusion.

Why hybrid: lexical search nails exact terminology ("RICE", "3NF", "idempotency
key") that embeddings blur, while dense search catches paraphrase ("how do I
decide what to build first"). RRF combines the two ranked lists without needing
score calibration between retrievers, which is what makes it robust when one
retriever is disabled entirely.

The index is a plain JSON artifact committed to the repo, so a serverless cold
start reads it straight off the read-only filesystem with no build step.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .chunking import Chunk
from .embeddings import dot

INDEX_VERSION = 2

BM25_K1 = 1.5
BM25_B = 0.75

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to for from by with
    as is are was were be been being it its it's do does did doing have has had having
    i you he she they we them their our your his her not no nor so too very can will just
    should would could about into over under again further once here there when where why how
    all any both each few more most other some such only own same s t don now
    """.split()
)


def tokenize(text: str) -> List[str]:
    """Lowercase, strip stopwords, and lightly de-pluralize.

    The same normalizer runs over documents and queries, so imperfect stemming
    ("process" -> "proces") still matches consistently on both sides.
    """
    tokens: List[str] = []
    for token in _TOKEN.findall(text.lower()):
        if len(token) < 2 or token in _STOPWORDS:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float
    lexical_rank: Optional[int] = None
    dense_rank: Optional[int] = None

    @property
    def retrievers(self) -> List[str]:
        found = []
        if self.lexical_rank is not None:
            found.append("bm25")
        if self.dense_rank is not None:
            found.append("dense")
        return found


class HybridStore:
    """In-memory hybrid index over a small, curated corpus."""

    def __init__(
        self,
        chunks: Optional[List[Chunk]] = None,
        vectors: Optional[Dict[str, List[float]]] = None,
        embedding_provider_name: str = "none",
        dimensions: int = 0,
    ):
        self.chunks: List[Chunk] = chunks or []
        self.vectors: Dict[str, List[float]] = vectors or {}
        self.embedding_provider_name = embedding_provider_name
        self.dimensions = dimensions

        self._doc_tokens: List[List[str]] = []
        self._term_frequencies: List[Counter] = []
        self._doc_frequency: Counter = Counter()
        self._avg_doc_length: float = 0.0
        self._build_lexical_index()

    # ---------------------------------------------------------------- build

    def _build_lexical_index(self) -> None:
        self._doc_tokens = [tokenize(chunk.embedding_text) for chunk in self.chunks]
        self._term_frequencies = [Counter(tokens) for tokens in self._doc_tokens]
        self._doc_frequency = Counter()
        for tokens in self._doc_tokens:
            for term in set(tokens):
                self._doc_frequency[term] += 1
        lengths = [len(tokens) for tokens in self._doc_tokens]
        self._avg_doc_length = (sum(lengths) / len(lengths)) if lengths else 0.0

    @property
    def size(self) -> int:
        return len(self.chunks)

    @property
    def has_dense(self) -> bool:
        return bool(self.vectors) and len(self.vectors) == len(self.chunks)

    # ------------------------------------------------------------ retrieval

    def _idf(self, term: str) -> float:
        total = len(self.chunks)
        df = self._doc_frequency.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (total - df + 0.5) / (df + 0.5))

    def search_lexical(self, query: str, limit: int, allowed: Optional[set[int]] = None) -> List[tuple[int, float]]:
        query_terms = tokenize(query)
        if not query_terms or not self.chunks:
            return []

        scores: List[tuple[int, float]] = []
        for index, frequencies in enumerate(self._term_frequencies):
            if allowed is not None and index not in allowed:
                continue
            doc_length = len(self._doc_tokens[index]) or 1
            score = 0.0
            for term in query_terms:
                tf = frequencies.get(term, 0)
                if tf == 0:
                    continue
                denominator = tf + BM25_K1 * (
                    1 - BM25_B + BM25_B * doc_length / (self._avg_doc_length or 1)
                )
                score += self._idf(term) * (tf * (BM25_K1 + 1)) / denominator
            if score > 0:
                scores.append((index, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]

    def search_dense(
        self,
        query_vector: Sequence[float],
        limit: int,
        allowed: Optional[set[int]] = None,
    ) -> List[tuple[int, float]]:
        if not self.has_dense or not query_vector:
            return []

        scores: List[tuple[int, float]] = []
        for index, chunk in enumerate(self.chunks):
            if allowed is not None and index not in allowed:
                continue
            vector = self.vectors.get(chunk.id)
            if not vector or len(vector) != len(query_vector):
                continue
            scores.append((index, dot(query_vector, vector)))

        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]

    def fuse(
        self,
        lexical: List[tuple[int, float]],
        dense: List[tuple[int, float]],
        *,
        rrf_k: int,
        limit: int,
        max_per_doc: int,
    ) -> List[ScoredChunk]:
        """Reciprocal Rank Fusion: score = sum over retrievers of 1/(k + rank)."""
        fused: Dict[int, ScoredChunk] = {}

        for rank, (index, _score) in enumerate(lexical, start=1):
            entry = fused.setdefault(index, ScoredChunk(self.chunks[index], 0.0))
            entry.score += 1.0 / (rrf_k + rank)
            entry.lexical_rank = rank

        for rank, (index, _score) in enumerate(dense, start=1):
            entry = fused.setdefault(index, ScoredChunk(self.chunks[index], 0.0))
            entry.score += 1.0 / (rrf_k + rank)
            entry.dense_rank = rank

        ranked = sorted(fused.values(), key=lambda item: item.score, reverse=True)

        # Cap chunks per source document so one verbose doc cannot crowd out the
        # rest of the corpus.
        selected: List[ScoredChunk] = []
        per_doc: Counter = Counter()
        for item in ranked:
            if per_doc[item.chunk.doc_id] >= max_per_doc:
                continue
            per_doc[item.chunk.doc_id] += 1
            selected.append(item)
            if len(selected) >= limit:
                break
        return selected

    def filter_indices(
        self,
        domains: Optional[Iterable[str]] = None,
        authorities: Optional[Iterable[str]] = None,
    ) -> Optional[set[int]]:
        """Metadata pre-filter. Returns None when no filter applies."""
        domain_set = {d.strip().lower() for d in domains} if domains else None
        authority_set = {a.strip().lower() for a in authorities} if authorities else None
        if not domain_set and not authority_set:
            return None

        allowed = {
            index
            for index, chunk in enumerate(self.chunks)
            if (not domain_set or chunk.domain.lower() in domain_set)
            and (not authority_set or chunk.authority.lower() in authority_set)
        }
        # An over-narrow filter that matches nothing would silently return no
        # context; fall back to the full corpus instead.
        return allowed or None

    @property
    def domains(self) -> List[str]:
        return sorted({chunk.domain for chunk in self.chunks})

    def documents(self) -> List[Dict[str, str]]:
        seen: Dict[str, Dict[str, str]] = {}
        for chunk in self.chunks:
            if chunk.doc_id not in seen:
                seen[chunk.doc_id] = {
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "domain": chunk.domain,
                    "authority": chunk.authority,
                }
        return sorted(seen.values(), key=lambda item: item["doc_id"])

    # --------------------------------------------------------- persistence

    def to_dict(self) -> Dict:
        return {
            "version": INDEX_VERSION,
            "embedding_provider": self.embedding_provider_name,
            "dimensions": self.dimensions,
            "chunk_count": len(self.chunks),
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "vectors": self.vectors,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "HybridStore":
        if not path.exists():
            return cls()

        data = json.loads(path.read_text(encoding="utf-8"))
        if int(data.get("version") or 0) != INDEX_VERSION:
            # Stale artifact: better to run lexical-only on an empty store than
            # to misinterpret a different layout.
            return cls()

        return cls(
            chunks=[Chunk.from_dict(item) for item in data.get("chunks") or []],
            vectors={key: list(value) for key, value in (data.get("vectors") or {}).items()},
            embedding_provider_name=data.get("embedding_provider") or "none",
            dimensions=int(data.get("dimensions") or 0),
        )
