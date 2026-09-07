"""RAG tool: grounded lookup into the product-management knowledge base."""
from __future__ import annotations

from typing import Any, Dict

from ..core.config.settings import settings
from .base import Tool, ToolContext, ToolResult

DOMAINS = [
    "discovery",
    "prioritization",
    "requirements",
    "metrics",
    "architecture",
    "data",
    "delivery",
    "quality",
]


async def _search(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = str(args.get("query") or "").strip()
    if not query:
        return ToolResult.error("`query` is required")

    if ctx.retriever is None or not ctx.retriever.available:
        return ToolResult(
            content="The knowledge base is unavailable. Rely on general best practice and say so explicitly.",
            ok=False,
        )

    domain = args.get("domain")
    domains = [domain] if isinstance(domain, str) and domain in DOMAINS else None
    k = args.get("k")
    limit = int(k) if isinstance(k, (int, float)) and 1 <= float(k) <= 8 else settings.RAG_TOP_K

    result = await ctx.retriever.retrieve(query, k=limit, domains=domains)
    if result.is_empty:
        return ToolResult(content=f"No knowledge-base passages matched '{query}'.")

    header = (
        f"{len(result.chunks)} passages for '{query}' "
        f"(retrievers: {', '.join(result.retrievers_used) or 'none'}). "
        "Cite them inline using their [S#] markers.\n\n"
    )
    return ToolResult(
        content=header + result.context,
        citations=result.citations,
        data={"query": query, "chunk_ids": [item.chunk.id for item in result.chunks]},
    )


search_pm_knowledge = Tool(
    name="search_pm_knowledge",
    description=(
        "Search a curated corpus of product-management and software-architecture "
        "references (RICE, MoSCoW, Kano, JTBD, PRD structure, INVEST, HEART, "
        "architecture patterns, API design, data modelling, estimation). Use it "
        "before making a framework, scoring, or architecture decision so the "
        "output follows established practice instead of guesswork. Returns "
        "passages with [S#] citation markers."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language question, e.g. 'how should acceptance criteria be written'",
            },
            "domain": {
                "type": "string",
                "enum": DOMAINS,
                "description": "Optional filter to one knowledge domain",
            },
            "k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 8,
                "description": "Number of passages to return (default 5)",
            },
        },
        "required": ["query"],
    },
    handler=_search,
)
