"""
Build the knowledge index artifact.

    python -m app.rag.ingest                 # BM25-only index (no API key needed)
    python -m app.rag.ingest --with-vectors  # adds dense vectors via the configured provider

The resulting JSON is committed so deployments need no build step and no
embedding provider at runtime.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow `python app/rag/ingest.py` in addition to `python -m app.rag.ingest`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config.settings import settings  # noqa: E402
from app.rag.chunking import load_knowledge_dir  # noqa: E402
from app.rag.embeddings import get_embedding_provider  # noqa: E402
from app.rag.store import HybridStore  # noqa: E402


async def build(with_vectors: bool, knowledge_dir: Path, output: Path) -> HybridStore:
    chunks = load_knowledge_dir(knowledge_dir)
    if not chunks:
        raise SystemExit(f"No markdown documents found in {knowledge_dir}")

    print(f"Chunked {len(chunks)} sections from {len(set(c.doc_id for c in chunks))} documents")

    vectors: dict[str, list[float]] = {}
    provider_name = "none"
    dimensions = 0

    if with_vectors:
        provider = get_embedding_provider()
        if not provider.enabled:
            raise SystemExit(
                "--with-vectors requires an embedding provider. Set OPENAI_API_KEY or "
                "JINA_API_KEY (and optionally EMBEDDING_PROVIDER) in backend/.env."
            )
        print(f"Embedding {len(chunks)} chunks with provider '{provider.name}'…")
        embedded = await provider.embed([chunk.embedding_text for chunk in chunks])
        if len(embedded) != len(chunks):
            raise SystemExit(f"Provider returned {len(embedded)} vectors for {len(chunks)} chunks")
        vectors = {chunk.id: vector for chunk, vector in zip(chunks, embedded)}
        provider_name = provider.name
        dimensions = len(embedded[0]) if embedded else 0

    store = HybridStore(chunks, vectors, provider_name, dimensions)
    store.save(output)

    size_kb = output.stat().st_size / 1024
    print(f"Wrote {output} ({size_kb:.0f} KB)")
    print(f"  chunks:  {store.size}")
    print(f"  domains: {', '.join(store.domains)}")
    print(f"  dense:   {'yes (' + provider_name + f', dim={dimensions})' if store.has_dense else 'no (BM25-only)'}")
    return store


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the RAG knowledge index")
    parser.add_argument("--with-vectors", action="store_true", help="Compute dense embeddings")
    parser.add_argument("--knowledge-dir", type=Path, default=settings.RAG_KNOWLEDGE_DIR)
    parser.add_argument("--output", type=Path, default=settings.RAG_INDEX_PATH)
    args = parser.parse_args()

    asyncio.run(build(args.with_vectors, args.knowledge_dir, args.output))


if __name__ == "__main__":
    main()
