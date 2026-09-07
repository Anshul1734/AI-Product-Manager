"""
Pluggable embedding providers for dense retrieval.

Groq serves no embeddings endpoint, so dense vectors come from a separate
provider. When no provider key is configured the app resolves to
`NoEmbeddings` and retrieval runs BM25-only -- degraded recall, but zero
external dependencies and no silent failure.
"""
from __future__ import annotations

import math
from typing import List, Optional, Protocol, Sequence

import httpx

from ..core.config.settings import settings
from ..core.logging.logger import app_logger


def normalize(vector: Sequence[float]) -> List[float]:
    """L2-normalize so cosine similarity reduces to a dot product."""
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude == 0:
        return [0.0] * len(vector)
    return [component / magnitude for component in vector]


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class EmbeddingProvider(Protocol):
    name: str
    dimensions: int

    @property
    def enabled(self) -> bool: ...

    async def embed(self, texts: Sequence[str], *, is_query: bool = False) -> List[List[float]]: ...


class NoEmbeddings:
    """Null provider: dense retrieval disabled."""

    name = "none"
    dimensions = 0

    @property
    def enabled(self) -> bool:
        return False

    async def embed(self, texts: Sequence[str], *, is_query: bool = False) -> List[List[float]]:
        return []


class _HttpEmbeddings:
    """Shared batching/transport logic for HTTP embedding APIs."""

    name = "http"
    dimensions = 0
    _url = ""
    _model = ""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self._api_key = api_key.strip()
        if model:
            self._model = model

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def _payload(self, batch: Sequence[str], is_query: bool) -> dict:
        raise NotImplementedError

    async def embed(self, texts: Sequence[str], *, is_query: bool = False) -> List[List[float]]:
        if not texts or not self.enabled:
            return []

        vectors: List[List[float]] = []
        batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
        async with httpx.AsyncClient(timeout=60.0) as client:
            for start in range(0, len(texts), batch_size):
                batch = list(texts[start : start + batch_size])
                response = await client.post(
                    self._url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=self._payload(batch, is_query),
                )
                if response.status_code >= 400:
                    raise RuntimeError(
                        f"{self.name} embeddings failed ({response.status_code}): {response.text[:200]}"
                    )
                data = response.json().get("data") or []
                for item in data:
                    vectors.append(normalize(item.get("embedding") or []))
        if vectors:
            self.dimensions = len(vectors[0])
        return vectors


class OpenAIEmbeddings(_HttpEmbeddings):
    name = "openai"
    _model = "text-embedding-3-small"

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model)
        self._url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"

    def _payload(self, batch: Sequence[str], is_query: bool) -> dict:
        return {"model": self._model, "input": list(batch)}


class JinaEmbeddings(_HttpEmbeddings):
    name = "jina"
    _model = "jina-embeddings-v3"
    _url = "https://api.jina.ai/v1/embeddings"

    def _payload(self, batch: Sequence[str], is_query: bool) -> dict:
        # Jina v3 is asymmetric: queries and documents use different adapters.
        return {
            "model": self._model,
            "task": "retrieval.query" if is_query else "retrieval.passage",
            "input": list(batch),
        }


def get_embedding_provider() -> EmbeddingProvider:
    """Build the provider implied by configuration."""
    provider = settings.resolved_embedding_provider()

    if provider == "openai" and (settings.OPENAI_API_KEY or "").strip():
        return OpenAIEmbeddings(settings.OPENAI_API_KEY, settings.EMBEDDING_MODEL)
    if provider == "jina" and (settings.JINA_API_KEY or "").strip():
        return JinaEmbeddings(settings.JINA_API_KEY, settings.EMBEDDING_MODEL)

    if provider not in {"none", "auto"}:
        app_logger.warning(
            "Embedding provider requested but no API key found; falling back to BM25-only retrieval",
            provider=provider,
        )
    return NoEmbeddings()
