"""Memory tool: recall past product plans relevant to the current idea."""
from __future__ import annotations

from typing import Any, Dict

from .base import Tool, ToolContext, ToolResult


async def _recall(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = str(args.get("query") or "").strip()
    if not query:
        return ToolResult.error("`query` is required")

    if ctx.memory is None:
        return ToolResult(content="Plan memory is disabled for this run.", ok=False)

    k = args.get("k")
    limit = int(k) if isinstance(k, (int, float)) and 1 <= float(k) <= 5 else 3

    matches = ctx.memory.search(query, k=limit, exclude_thread=None)
    if not matches:
        return ToolResult(content="No prior plans resemble this idea. Treat it as greenfield.")

    lines = [f"{len(matches)} prior plan(s) with overlapping subject matter:", ""]
    for entry, score in matches:
        lines.append(f"- {entry.product_name} (relevance {score})")
        lines.append(f"  Original idea: {entry.idea[:180]}")
        if entry.problem_statement:
            lines.append(f"  Problem framing used: {entry.problem_statement[:180]}")
        if entry.top_features:
            lines.append(f"  Top-ranked features: {', '.join(entry.top_features[:4])}")
        if entry.tech_stack:
            lines.append(f"  Stack chosen: {', '.join(entry.tech_stack[:5])}")
        if entry.quality_score is not None:
            lines.append(f"  Review score: {entry.quality_score}/10")
        lines.append("")

    lines.append(
        "Reuse what worked and differentiate deliberately -- do not copy a prior plan "
        "onto a different problem."
    )
    return ToolResult(
        content="\n".join(lines),
        data={"matches": [entry.entry_id for entry, _ in matches]},
    )


recall_similar_plans = Tool(
    name="recall_similar_plans",
    description=(
        "Search previously generated product plans for ones addressing a similar "
        "problem, audience, or domain. Use it early to avoid re-deriving decisions "
        "already made and to keep terminology consistent across related products."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The current product idea, or a phrase describing its domain",
            },
            "k": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Max results (default 3)"},
        },
        "required": ["query"],
    },
    handler=_recall,
)
