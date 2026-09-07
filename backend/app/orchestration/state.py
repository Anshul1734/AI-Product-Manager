"""
LangGraph state schema.

The graph fans out — `analyst` and `prioritizer` both run off the vision in the
same superstep — so every key that more than one node writes needs a reducer.
Without one, LangGraph raises `InvalidUpdateError` on the concurrent write
rather than silently picking a winner, which is the behaviour you want but does
mean the trace, citation, token and error channels all have to be declared as
accumulating.

Artifact keys (`vision`, `prd`, …) are each written by exactly one node, so they
take the default last-write-wins channel.
"""
from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from ..schemas.artifacts import (
    PRD,
    AgentStep,
    Citation,
    Critique,
    FeaturePriorities,
    ProductVision,
    SystemArchitecture,
    Tickets,
)


class Depth(str, Enum):
    """How much work to do.

    Trades latency for rigour, but on a token-metered account it also decides
    whether a run fits a request budget — see DEPTH_MODEL_ROLES.
    """

    QUICK = "quick"        # 4 agents spread across all 3 buckets; no pacing stalls
    STANDARD = "standard"  # 6 agents plus a quality review; may pace
    DEEP = "deep"          # adds a bounded refine pass over weak artifacts

    @classmethod
    def parse(cls, value: Any) -> "Depth":
        try:
            return cls(str(value or "standard").strip().lower())
        except ValueError:
            return cls.STANDARD


def merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """Reducer for the error channel: later writes win per key."""
    return {**(left or {}), **(right or {})}


def merge_unique(left: List[str], right: List[str]) -> List[str]:
    """Reducer for set-like string channels, preserving first-seen order."""
    seen = list(left or [])
    for item in right or []:
        if item not in seen:
            seen.append(item)
    return seen


class PipelineState(TypedDict, total=False):
    # --- inputs (written once, before the graph starts) ---
    idea: str
    thread_id: str
    depth: str

    # --- artifacts: single-writer, so no reducer needed ---
    vision: Optional[ProductVision]
    prd: Optional[PRD]
    priorities: Optional[FeaturePriorities]
    architecture: Optional[SystemArchitecture]
    tickets: Optional[Tickets]
    critique: Optional[Critique]

    # --- shared retrieval context ---
    grounding: str
    retrievers_used: Annotated[List[str], merge_unique]

    # --- trace and metrics: written concurrently, so reducers are required ---
    steps: Annotated[List[AgentStep], operator.add]
    citations: Annotated[List[Citation], operator.add]
    errors: Annotated[Dict[str, str], merge_dicts]
    prompt_tokens: Annotated[int, operator.add]
    completion_tokens: Annotated[int, operator.add]
    refined: Annotated[List[str], operator.add]


def initial_state(idea: str, thread_id: str, depth: Depth) -> PipelineState:
    """Every channel seeded, so nodes can read without KeyError guards."""
    return {
        "idea": idea,
        "thread_id": thread_id,
        "depth": depth.value,
        "vision": None,
        "prd": None,
        "priorities": None,
        "architecture": None,
        "tickets": None,
        "critique": None,
        "grounding": "",
        "retrievers_used": [],
        "steps": [],
        "citations": [],
        "errors": {},
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "refined": [],
    }


def dedupe_citations(citations: List[Citation]) -> List[Citation]:
    """Collapse repeats across agents and renumber markers sequentially.

    Runs at assembly time rather than in the reducer: a reducer must stay
    associative and commutative, and renumbering is neither.
    """
    best: Dict[str, Citation] = {}
    for citation in citations or []:
        key = f"{citation.doc_id}|{citation.heading}"
        if key not in best or citation.score > best[key].score:
            best[key] = citation

    ordered = sorted(best.values(), key=lambda item: item.score, reverse=True)
    return [
        Citation(
            marker=f"S{index}",
            doc_id=item.doc_id,
            title=item.title,
            heading=item.heading,
            score=item.score,
        )
        for index, item in enumerate(ordered, start=1)
    ]
