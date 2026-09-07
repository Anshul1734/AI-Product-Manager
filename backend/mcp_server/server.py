"""
MCP server exposing the AI Product Manager as tools, resources, and prompts.

This is the inbound half of the project's MCP support: it lets any MCP client
(Claude Desktop, Claude Code, an IDE extension) drive the agent pipeline and
query the knowledge base directly, so product planning becomes something you can
invoke mid-conversation rather than a separate web app you context-switch into.
The outbound half -- consuming *other* people's MCP servers -- lives in
`app/tools/mcp_bridge.py`.

Run it:
    cd backend
    pip install -r requirements-dev.txt
    python -m mcp_server.server

Register it with Claude Desktop / Claude Code -- see mcp_server/README.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    raise SystemExit(
        "The `mcp` package is required to run this server.\n"
        "Install it with:  pip install -r requirements-dev.txt"
    )

from app.core.config.settings import settings  # noqa: E402
from app.memory.store import get_memory  # noqa: E402
from app.orchestration.pipeline import ProductPlanPipeline  # noqa: E402
from app.orchestration.state import Depth  # noqa: E402
from app.rag.retriever import Retriever, get_store  # noqa: E402
from app.services.export_service import ExportService  # noqa: E402
from app.tools.scoring import IMPACT_SCALE, compute_rice  # noqa: E402

mcp = FastMCP(
    "ai-product-manager",
    instructions=(
        "Multi-agent product planning. `generate_product_plan` runs a graph of "
        "specialist agents (vision, PRD, RICE prioritization, architecture, backlog, "
        "quality review) over a product idea and returns a complete PRD. "
        "`search_pm_knowledge` queries the same product-management corpus the agents "
        "use, for grounding a discussion without running the full pipeline."
    ),
)

_exporter = ExportService()


@mcp.tool()
async def generate_product_plan(idea: str, depth: str = "standard", thread_id: Optional[str] = None) -> str:
    """Run the full multi-agent pipeline on a product idea and return a PRD.

    Args:
        idea: The product idea. More context produces a better plan.
        depth: "quick" (4 agents, fastest), "standard" (6 agents with a quality
            review), or "deep" (adds a refinement pass over weak artifacts).
        thread_id: Reuse a thread so the planner can build on earlier runs.

    Returns a complete product requirements document in Markdown, covering the
    problem, personas, user stories with acceptance criteria, RICE-scored
    features, architecture, and a delivery backlog.
    """
    if not settings.llm_configured:
        return "ERROR: GROQ_API_KEY is not set. Add it to backend/.env before running the pipeline."

    payload = await ProductPlanPipeline().run(
        idea, thread_id=thread_id, depth=Depth.parse(depth)
    )

    markdown = _exporter.prd_markdown(payload, idea).decode("utf-8")
    meta = payload.get("meta") or {}
    quality = payload.get("quality") or {}

    footer = [
        "",
        "---",
        "",
        "### Run details",
        "",
        f"- Agents: {', '.join(meta.get('agents_run') or []) or 'none'}",
        f"- Depth: {meta.get('depth')}",
        f"- Duration: {meta.get('execution_time')}s",
        f"- Tokens: {meta.get('total_tokens')}",
    ]
    retrieval = meta.get("retrieval") or {}
    if retrieval.get("enabled"):
        footer.append(
            f"- Retrieval: {retrieval.get('sources_cited')} sources cited from "
            f"{retrieval.get('corpus_chunks')} indexed passages "
            f"({'hybrid' if retrieval.get('dense') else 'BM25-only'})"
        )
    if quality:
        footer.append(f"- Review score: {quality.get('overall')}/10 ({quality.get('grade')})")
    if meta.get("refined_artifacts"):
        footer.append(f"- Revised after review: {', '.join(meta['refined_artifacts'])}")
    if meta.get("errors"):
        footer.append(f"- Non-fatal errors: {json.dumps(meta['errors'])}")

    return markdown + "\n".join(footer)


@mcp.tool()
async def search_pm_knowledge(query: str, domain: Optional[str] = None, k: int = 5) -> str:
    """Search the product-management and architecture knowledge corpus.

    Hybrid retrieval (BM25 plus dense vectors when configured) over curated
    references on prioritization, discovery, requirements, metrics, architecture,
    data modelling, and delivery planning.

    Args:
        query: A natural-language question.
        domain: Optional filter -- one of discovery, prioritization, requirements,
            metrics, architecture, data, delivery, quality.
        k: Number of passages to return (1-10).
    """
    retriever = Retriever()
    if not retriever.available:
        return "ERROR: knowledge index not built. Run: python -m app.rag.ingest"

    result = await retriever.retrieve(
        query, k=max(1, min(10, k)), domains=[domain] if domain else None
    )
    if result.is_empty:
        return f"No passages matched '{query}'."

    lines = [
        f"**{len(result.chunks)} passage(s)** for _{query}_ "
        f"(retrievers: {', '.join(result.retrievers_used)})",
        "",
    ]
    for scored, citation in zip(result.chunks, result.citations):
        chunk = scored.chunk
        lines += [
            f"### [{citation.marker}] {chunk.title} — {chunk.heading}",
            f"_{chunk.domain} · {chunk.authority} · matched by {', '.join(scored.retrievers)}_",
            "",
            chunk.text,
            "",
        ]
    return "\n".join(lines)


@mcp.tool()
def score_features_rice(features: List[Dict[str, Any]]) -> str:
    """Compute and rank RICE scores for a list of features.

    RICE = (reach x impact x confidence/100) / effort. The arithmetic and sorting
    happen in Python, so the ranking is exact.

    Args:
        features: Objects with `name`, `reach` (users per quarter), `impact`
            (3, 2, 1, 0.5, or 0.25), `confidence` (10-100), `effort`
            (person-months), and optionally `description` and `justification`.
    """
    scored = compute_rice(features)
    if not scored:
        return "ERROR: no features with a usable `name` were provided."

    lines = [
        "| # | Feature | Reach | Impact | Conf. | Effort | Score |",
        "|---|---------|-------|--------|-------|--------|-------|",
    ]
    for item in scored:
        rice = item["rice"]
        lines.append(
            f"| {item['rank']} | {item['name']} | {rice['reach']:g} | "
            f"{rice['impact']:g} ({IMPACT_SCALE[rice['impact']]}) | {rice['confidence']:g}% | "
            f"{rice['effort']:g} | **{rice['score']}** |"
        )

    justified = [item for item in scored if item.get("justification")]
    if justified:
        lines += ["", "**Rationale**", ""]
        lines += [f"- **{item['name']}**: {item['justification']}" for item in justified]

    return "\n".join(lines)


@mcp.tool()
def recall_similar_plans(query: str, k: int = 3) -> str:
    """Search previously generated product plans for similar problems or domains.

    Args:
        query: A product idea or a phrase describing the domain.
        k: Number of results (1-10).
    """
    if not settings.MEMORY_ENABLED:
        return "Memory is disabled (MEMORY_ENABLED=false)."

    matches = get_memory().search(query, k=max(1, min(10, k)))
    if not matches:
        return f"No stored plans resemble '{query}'."

    lines = [f"**{len(matches)} prior plan(s)**", ""]
    for entry, score in matches:
        lines += [
            f"### {entry.product_name}  _(relevance {score})_",
            f"- Idea: {entry.idea}",
            f"- Problem: {entry.problem_statement}",
        ]
        if entry.top_features:
            lines.append(f"- Top features: {', '.join(entry.top_features)}")
        if entry.tech_stack:
            lines.append(f"- Stack: {', '.join(entry.tech_stack)}")
        if entry.quality_score is not None:
            lines.append(f"- Review score: {entry.quality_score}/10")
        lines += [f"- Created: {entry.created_at.strftime('%Y-%m-%d %H:%M UTC')}", ""]
    return "\n".join(lines)


@mcp.tool()
def list_knowledge_documents() -> str:
    """List the documents in the retrieval corpus, with their domains."""
    store = get_store()
    if store.size == 0:
        return "ERROR: knowledge index not built. Run: python -m app.rag.ingest"

    lines = [
        f"**{len(store.documents())} documents / {store.size} passages** "
        f"({'hybrid retrieval' if store.has_dense else 'BM25-only'})",
        "",
        "| Document | Domain | Authority | URI |",
        "|---|---|---|---|",
    ]
    for doc in store.documents():
        lines.append(
            f"| {doc['title']} | {doc['domain']} | {doc['authority']} | `pmkb://{doc['doc_id']}` |"
        )
    return "\n".join(lines)


@mcp.resource("pmkb://{doc_id}")
def knowledge_document(doc_id: str) -> str:
    """Full text of one knowledge-base document."""
    store = get_store()
    chunks = [chunk for chunk in store.chunks if chunk.doc_id == doc_id]
    if not chunks:
        available = ", ".join(doc["doc_id"] for doc in store.documents())
        return f"No document '{doc_id}'. Available: {available}"

    lines = [f"# {chunks[0].title}", "", f"_{chunks[0].domain} · {chunks[0].authority}_", ""]
    for chunk in chunks:
        lines += [f"## {chunk.heading}", "", chunk.text, ""]
    return "\n".join(lines)


@mcp.prompt()
def product_discovery(idea: str) -> str:
    """Interrogate a product idea before committing to building it."""
    return (
        f"I am considering building this product:\n\n{idea}\n\n"
        "Before generating a plan, pressure-test the idea with me:\n"
        "1. Use search_pm_knowledge to pull the guidance on problem framing and "
        "opportunity sizing.\n"
        "2. Tell me whether my idea states a problem or just a solution, and rewrite "
        "it as a testable problem statement.\n"
        "3. Identify the single assumption that would most cheaply invalidate this, "
        "and how I would test it this week.\n"
        "4. Only once we agree the problem is real, call generate_product_plan."
    )


@mcp.prompt()
def prd_review(prd: str) -> str:
    """Review an existing PRD against established practice."""
    return (
        f"Review this PRD:\n\n{prd}\n\n"
        "Use search_pm_knowledge to retrieve the standards for PRD structure, INVEST "
        "user stories, acceptance criteria, and success metrics. Then score it 0-10 on "
        "completeness, consistency, specificity, and feasibility, citing the retrieved "
        "guidance. Be specific about what is missing and give me the exact edits to "
        "make. Do not be generous with the scores."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
