"""
Pipeline endpoints.

`/generate` runs the graph and returns the finished plan. `/generate/stream`
runs the same graph but emits Server-Sent Events as each agent starts, calls a
tool, or finishes -- which is what makes the multi-agent work visible instead of
a spinner, and keeps the connection active inside a serverless request budget.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncIterator, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..llm.errors import LLMNotConfiguredError, LLMRateLimitError
from ..orchestration.pipeline import ProductPlanPipeline
from ..orchestration.state import Depth
from ..schemas.requests import ProductIdeaRequest, ValidationRequest
from ..schemas.responses import ValidationResponse, WorkflowResponse

router = APIRouter(tags=["workflow"])

_SENTINEL = object()


def _friendly_error(exc: Exception) -> str:
    """Turn a provider error into something a user can act on.

    Groq's rate-limit bodies are long and mention organisation ids and internal
    tier names. The distinction that matters to someone looking at the UI is
    simply whether to wait, or to go set a key.
    """
    if isinstance(exc, LLMNotConfiguredError):
        return str(exc)

    text = str(exc)
    if isinstance(exc, LLMRateLimitError) or "rate_limit" in text or "Rate limit" in text:
        wait = re.search(r"try again in ([0-9hms.]+)", text)
        window = "daily" if "per day" in text or "TPD" in text else "per-minute"
        suffix = f" Retry in about {wait.group(1)}." if wait else ""
        return (
            f"The model's {window} token budget is used up.{suffix} "
            "Groq's free tier allows 8,000 tokens per minute and 200,000 per day per model. "
            "Try 'quick' depth, wait for the window to reset, or raise the limits on a paid tier."
        )

    return text[:400]


def _pipeline() -> ProductPlanPipeline:
    # Constructed per request: agents hold per-run mutable state (fast-model
    # flags, MCP tool lists) that must not leak between concurrent requests.
    return ProductPlanPipeline()


@router.post("/generate", response_model=WorkflowResponse)
async def generate(request: ProductIdeaRequest) -> WorkflowResponse:
    """Run the full agent pipeline and return the completed plan."""
    depth = Depth.parse(request.depth)
    app_logger.info("Generate requested", depth=depth.value, thread_id=request.thread_id, idea=request.idea[:160])

    try:
        payload = await _pipeline().run(request.idea, thread_id=request.thread_id, depth=depth)
        return WorkflowResponse(
            success=True,
            message="Product plan generated",
            data=payload,
            execution_time=(payload.get("meta") or {}).get("execution_time"),
            thread_id=(payload.get("meta") or {}).get("thread_id"),
        )
    except Exception as exc:
        app_logger.error("Generation failed", error=str(exc)[:400], error_type=type(exc).__name__)
        return WorkflowResponse(
            success=False, message=_friendly_error(exc), error_type=type(exc).__name__
        )


@router.post("/generate/stream")
async def generate_stream(request: ProductIdeaRequest) -> StreamingResponse:
    """Run the pipeline, streaming agent progress as Server-Sent Events."""
    depth = Depth.parse(request.depth)

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue = asyncio.Queue()

        async def sink(event: Dict[str, Any]) -> None:
            await queue.put(event)

        async def producer() -> None:
            try:
                payload = await _pipeline().run(
                    request.idea, thread_id=request.thread_id, depth=depth, on_event=sink
                )
                await queue.put({"type": "complete", "data": payload})
            except Exception as exc:
                app_logger.error("Streamed generation failed", error=str(exc)[:400])
                await queue.put(
                    {"type": "error", "message": _friendly_error(exc), "error_type": type(exc).__name__}
                )
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(producer())
        yield _sse({"type": "start", "depth": depth.value, "idea": request.idea[:200]})

        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Keep intermediaries from closing an idle connection while a
                    # slow agent is still thinking.
                    yield ": keep-alive\n\n"
                    continue
                if item is _SENTINEL:
                    break
                yield _sse(item)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_idea(request: ValidationRequest) -> ValidationResponse:
    """Cheap heuristic check so users can improve an idea before spending a run."""
    idea = request.idea.strip()
    lowered = idea.lower()
    issues: list[str] = []
    suggestions: list[str] = []

    if len(idea) < 10:
        issues.append("Too short to work with")
        suggestions.append("Describe what the product does and who it is for, in a sentence or two")
    if len(idea) > 1200:
        issues.append("Very long; the important signal may get diluted")
        suggestions.append("Lead with the problem and the user, and trim implementation detail")
    if not any(word in lowered for word in ("problem", "struggle", "cannot", "can't", "difficult", "waste", "slow", "manual", "need")):
        issues.append("No problem is stated, only a solution")
        suggestions.append("Say what breaks today: 'support agents cannot see order history, so refunds take 3 days'")
    if not any(word in lowered for word in ("for", "user", "customer", "team", "people", "manager", "developer", "student", "business")):
        issues.append("No target user identified")
        suggestions.append("Name the role that feels the pain, not 'everyone'")

    return ValidationResponse(
        success=True,
        valid=not issues,
        issues=issues,
        suggestions=suggestions,
        confidence_score=round(max(0.0, 1.0 - 0.22 * len(issues)), 2),
        message="Idea looks workable" if not issues else "Idea could be sharpened",
    )


@router.get("/pipeline")
async def describe_pipeline() -> Dict[str, Any]:
    """Introspect the agent graph, tools, and depth levels."""
    pipeline = _pipeline()
    return {
        "success": True,
        "data": {
            "orchestrator": "langgraph",
            "graph": _graph_topology(pipeline),
            "agents": [
                {
                    "name": agent.name,
                    "label": agent.label,
                    "tools": list(agent.tool_names),
                    "model": agent.model,
                    "model_role": agent.model_role,
                    "output_schema": agent.output_model.__name__,
                }
                for agent in (*pipeline.agents.values(), pipeline.critic)
            ],
            "depths": {
                "quick": "5 agents on the small model, no quality review",
                "standard": "6 agents across three models, including a quality review",
                "deep": "adds one refinement pass over artifacts scoring below threshold",
            },
            "budget": {
                "tokens_per_minute_per_model": settings.GROQ_TPM_LIMIT,
                "max_tool_iterations": settings.MAX_TOOL_ITERATIONS,
                "note": (
                    "Token budgets are enforced per model, so agents are spread across "
                    "models to widen the effective ceiling."
                ),
            },
            "retrieval": {
                "enabled": pipeline.retriever.available,
                "corpus_chunks": pipeline.retriever.store.size,
                "documents": pipeline.retriever.store.documents(),
                "dense": pipeline.retriever.store.has_dense,
                "provider": pipeline.retriever.store.embedding_provider_name,
            },
        },
    }


@router.get("/threads/{thread_id}")
async def read_thread(thread_id: str) -> Dict[str, Any]:
    """Read a run's checkpointed state.

    LangGraph persists each superstep against the thread id, so a finished (or
    interrupted) run can be inspected afterwards without re-running it.
    """
    graph = _pipeline().build_graph()
    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No checkpoint for thread '{thread_id}'")

    values = snapshot.values
    return {
        "success": True,
        "data": {
            "thread_id": thread_id,
            "next_nodes": list(snapshot.next or []),
            "depth": values.get("depth"),
            "idea": values.get("idea"),
            "completed_agents": [step.agent for step in values.get("steps") or []],
            "artifacts_present": {
                key: values.get(key) is not None
                for key in ("vision", "prd", "priorities", "architecture", "tickets", "critique")
            },
            "errors": values.get("errors") or {},
            "tokens": (values.get("prompt_tokens") or 0) + (values.get("completion_tokens") or 0),
        },
    }


def _graph_topology(pipeline: ProductPlanPipeline) -> Dict[str, Any]:
    """Nodes and edges as LangGraph itself reports them."""
    graph = pipeline.build_graph().get_graph()
    return {
        "nodes": [node for node in graph.nodes if not node.startswith("__")],
        "edges": [
            {"from": edge.source, "to": edge.target, "conditional": bool(edge.conditional)}
            for edge in graph.edges
        ],
    }


def _sse(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
