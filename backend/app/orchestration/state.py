"""Typed state threaded through the agent graph."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..llm.client import Usage
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
    whether a run fits a serverless request budget -- see DEPTH_MODEL_ROLES.
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


@dataclass
class RunState:
    idea: str
    thread_id: str = field(default_factory=lambda: f"thread_{uuid.uuid4().hex[:12]}")
    depth: Depth = Depth.STANDARD

    vision: Optional[ProductVision] = None
    prd: Optional[PRD] = None
    priorities: Optional[FeaturePriorities] = None
    architecture: Optional[SystemArchitecture] = None
    tickets: Optional[Tickets] = None
    critique: Optional[Critique] = None

    grounding: str = ""
    steps: List[AgentStep] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    refined: List[str] = field(default_factory=list)
    retrievers_used: List[str] = field(default_factory=list)

    started_at: float = field(default_factory=time.perf_counter)

    @property
    def elapsed(self) -> float:
        return round(time.perf_counter() - self.started_at, 3)

    @property
    def review_enabled(self) -> bool:
        return self.depth in (Depth.STANDARD, Depth.DEEP)

    @property
    def refine_enabled(self) -> bool:
        return self.depth is Depth.DEEP

    def record_step(self, step: AgentStep) -> None:
        self.steps.append(step)

    def merge_citations(self, citations: List[Citation]) -> None:
        """Union citations across agents, keyed by source section."""
        existing = {f"{c.doc_id}|{c.heading}" for c in self.citations}
        for citation in citations:
            key = f"{citation.doc_id}|{citation.heading}"
            if key not in existing:
                existing.add(key)
                self.citations.append(citation)
        for index, citation in enumerate(self.citations, start=1):
            citation.marker = f"S{index}"
