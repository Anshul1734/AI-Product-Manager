"""
LangSmith tracing.

LangGraph traces each graph node by itself once tracing is on. But every LLM
call, tool call, retrieval and embedding in this project goes through its own
httpx clients, which LangSmith cannot see into, so on their own those nodes
would be opaque boxes. The call sites are wrapped with `traceable` so a run
reads as one tree:

    product_plan                        (graph run: thread, depth, workspace)
      planner                           (graph node)
        retrieve                        (retriever: pre-grounding passages)
          embed                         (embedding: provider, count)
        groq.chat · planner research 1  (llm: prompt, response, tokens, model)
        search_pm_knowledge             (tool: arguments, result)
          retrieve ...
        groq.chat · planner emit        (llm; "repair N" on a schema retry)
      analyst ...

`traceable` is a pass-through while tracing is disabled (see
`Settings.export_tracing_env`), so none of this costs anything when off.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from .config.settings import settings
from .logging.logger import app_logger

__all__ = ["traceable", "without", "annotate", "flush"]


def without(*keys: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """`process_inputs` hook dropping arguments that do not belong in a trace:
    `self`, raw upload bytes, provider clients."""

    def process(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in inputs.items() if key not in {"self", *keys}}

    return process


def annotate(**metadata: Any) -> None:
    """Attach metadata to the current span -- for facts only known mid-call,
    such as which model actually answered after a budget fallback."""
    run = get_current_run_tree()
    if run is not None:
        run.metadata.update({key: value for key, value in metadata.items() if value is not None})


def flush() -> None:
    """Send buffered traces before the process exits."""
    if not settings.tracing_enabled:
        return
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        from langsmith.run_trees import get_cached_client

        wait_for_all_tracers()
        get_cached_client().flush()
    except Exception as exc:  # pragma: no cover - best effort at shutdown
        app_logger.warning("Could not flush LangSmith traces", error=str(exc)[:200])
