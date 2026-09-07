"""
The product-management agent pipeline.

    retrieve ──> planner ──┬─> analyst ──> architect ──┐
                           │                            ├─> tickets ─> critic? ─> refine?
                           └─> prioritizer ─────────────┘

`analyst` and `prioritizer` both depend only on the vision, so they run
concurrently. `critic` and `refine` are gated on the requested depth and are
non-critical: a failed review degrades the response to an unreviewed plan rather
than losing the work.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence

from ..agents import (
    AnalystAgent,
    ArchitectAgent,
    CriticAgent,
    PlannerAgent,
    PrioritizerAgent,
    TicketGeneratorAgent,
)
from ..agents.base import AgentRunResult, BaseAgent
from ..agents.digests import review_digest
from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..llm.client import LLMClient
from ..memory.store import MemoryEntry, get_memory
from ..rag.retriever import Retriever
from ..schemas.artifacts import AgentStep
from ..tools.base import ToolContext
from ..tools.mcp_bridge import MCPBridge
from ..tools.registry import ToolRegistry
from .graph import Graph, Node
from .state import Depth, RunState

EventSink = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]

#: Knowledge domains each agent is pre-grounded with, in addition to whatever it
#: chooses to look up via `search_pm_knowledge`. Pre-grounding costs no LLM call
#: and guarantees a floor of relevant context even if the model skips its tools.
GROUNDING_DOMAINS: Dict[str, Sequence[str]] = {
    "planner": ("discovery",),
    "analyst": ("requirements",),
    "prioritizer": ("prioritization",),
    "architect": ("architecture", "data"),
    "ticket_generator": ("delivery",),
}

#: Model-role assignment per depth.
#:
#: Provider token budgets are per-model, so these assignments are a scheduling
#: decision, not just a quality one. `quick` deliberately spreads its four
#: agents across all three buckets so no bucket is asked for more than it holds
#: in a minute -- that is what keeps a run inside a serverless request budget.
#: `standard` and `deep` add agents and accept that the primary bucket may pace.
#:
#: The two largest schemas (architecture, backlog) stay on gpt-oss models at
#: every depth: smaller models produce malformed JSON at that size often enough
#: that the repair round costs more than the bigger model would have.
DEPTH_MODEL_ROLES: Dict[str, Dict[str, str]] = {
    "quick": {
        "planner": "primary",
        "analyst": "primary",
        "architect": "fast",
        "ticket_generator": "alt",
    },
    "standard": {
        "planner": "primary",
        "analyst": "primary",
        "prioritizer": "alt",
        "architect": "primary",
        "ticket_generator": "fast",
        "critic": "alt",
    },
}
DEPTH_MODEL_ROLES["deep"] = DEPTH_MODEL_ROLES["standard"]

#: Agents skipped entirely at a given depth, to stay inside the budget.
DEPTH_SKIPS: Dict[str, frozenset] = {
    "quick": frozenset({"prioritizer", "critic", "refine"}),
    "standard": frozenset({"refine"}),
    "deep": frozenset(),
}

#: Which agent owns each critiqued artifact, for the refine pass.
ARTIFACT_OWNERS = {
    "plan": "planner",
    "prd": "analyst",
    "features_detailed": "prioritizer",
    "architecture": "architect",
    "tickets": "ticket_generator",
}


class ProductPlanPipeline:
    """Builds and executes the agent graph for one product idea."""

    def __init__(self, retriever: Optional[Retriever] = None):
        self.retriever = retriever or Retriever()
        self.memory = get_memory() if settings.MEMORY_ENABLED else None

        self.planner = PlannerAgent()
        self.analyst = AnalystAgent()
        self.prioritizer = PrioritizerAgent()
        self.architect = ArchitectAgent()
        self.ticket_generator = TicketGeneratorAgent()
        self.critic = CriticAgent()

        #: Agents that own a regenerable artifact, keyed by name. The critic is
        #: excluded: it reviews artifacts rather than producing one.
        self.agents: Dict[str, BaseAgent] = {
            agent.name: agent
            for agent in (
                self.planner,
                self.analyst,
                self.prioritizer,
                self.architect,
                self.ticket_generator,
            )
        }

    # ------------------------------------------------------------------ entry

    async def run(
        self,
        idea: str,
        *,
        thread_id: Optional[str] = None,
        depth: Depth = Depth.STANDARD,
        on_event: EventSink = None,
    ) -> Dict[str, Any]:
        state = RunState(idea=idea.strip(), depth=depth)
        if thread_id:
            state.thread_id = thread_id

        for name, role in DEPTH_MODEL_ROLES.get(depth.value, {}).items():
            agent = self.agents.get(name) or (self.critic if name == "critic" else None)
            if agent is not None:
                agent.model_role = role

        async with LLMClient() as llm, MCPBridge() as bridge:
            registry = ToolRegistry(
                ToolContext(retriever=self.retriever, memory=self.memory, thread_id=state.thread_id)
            )
            if bridge.tools:
                registry.register_many(bridge.tools)
                # External tools go to the ticket agent, which is the one with a
                # reason to reach outside: filing the work it just wrote.
                self.ticket_generator.tool_names = tuple(
                    [*self.ticket_generator.tool_names, *(tool.name for tool in bridge.tools)]
                )

            graph = self.build_graph(llm, registry)
            app_logger.info(
                "Executing agent graph",
                thread_id=state.thread_id,
                depth=depth.value,
                layers=graph.describe(),
                tools=registry.names,
            )
            await graph.run(state, on_event)

        self._persist(state)
        return self.assemble(state)

    # ------------------------------------------------------------------ graph

    def build_graph(self, llm: Optional[LLMClient] = None, registry: Optional[ToolRegistry] = None) -> Graph:
        """Assemble the node graph.

        `llm` and `registry` are only captured by the node closures, never called
        during construction, so passing None yields a graph that is valid for
        topology introspection.
        """
        return Graph(
            [
                Node(
                    name="retrieve",
                    label="Retrieving domain knowledge",
                    run=self._node_retrieve,
                    critical=False,
                ),
                Node(
                    name="planner",
                    label="Framing the product vision",
                    run=self._make_agent_node(self.planner, llm, registry, self._planner_inputs, "vision"),
                    after=("retrieve",),
                ),
                Node(
                    name="analyst",
                    label="Writing the PRD",
                    run=self._make_agent_node(self.analyst, llm, registry, self._analyst_inputs, "prd"),
                    depends_on=("planner",),
                ),
                Node(
                    name="prioritizer",
                    label="Scoring and ranking features",
                    run=self._make_agent_node(
                        self.prioritizer, llm, registry, self._prioritizer_inputs, "priorities"
                    ),
                    depends_on=("planner",),
                    when=_enabled("prioritizer"),
                    critical=False,
                ),
                Node(
                    name="architect",
                    label="Designing the architecture",
                    run=self._make_agent_node(
                        self.architect, llm, registry, self._architect_inputs, "architecture"
                    ),
                    depends_on=("analyst",),
                ),
                Node(
                    name="ticket_generator",
                    label="Building the delivery backlog",
                    run=self._make_agent_node(
                        self.ticket_generator, llm, registry, self._tickets_inputs, "tickets"
                    ),
                    depends_on=("architect",),
                    after=("prioritizer",),
                ),
                Node(
                    name="critic",
                    label="Reviewing plan quality",
                    run=self._make_agent_node(self.critic, llm, registry, self._critic_inputs, "critique"),
                    depends_on=("ticket_generator",),
                    when=_enabled("critic"),
                    critical=False,
                ),
                Node(
                    name="refine",
                    label="Revising weak artifacts",
                    run=self._make_refine_node(llm, registry),
                    depends_on=("critic",),
                    when=_enabled("refine"),
                    critical=False,
                ),
            ]
        )

    # ------------------------------------------------------------------ nodes

    async def _node_retrieve(self, state: RunState) -> None:
        """Pre-fetch shared grounding. No LLM call."""
        if not self.retriever.available:
            return
        result = await self.retriever.retrieve(
            f"product discovery problem framing target users for: {state.idea}",
            k=settings.RAG_TOP_K,
        )
        state.grounding = result.context
        state.retrievers_used = result.retrievers_used
        state.merge_citations(result.citations)
        state.record_step(
            AgentStep(
                agent="retrieve",
                label="Retrieving domain knowledge",
                duration_seconds=0.0,
                citations=result.citations,
                note=(
                    f"{len(result.chunks)} passages via {', '.join(result.retrievers_used) or 'none'}"
                    if result.chunks
                    else "knowledge base unavailable"
                ),
            )
        )

    def _make_agent_node(
        self,
        agent: BaseAgent,
        llm: LLMClient,
        registry: ToolRegistry,
        input_builder: Callable[[RunState], Dict[str, Any]],
        target: str,
    ) -> Callable[[RunState], Awaitable[None]]:
        async def node(state: RunState) -> None:
            grounding = await self._grounding_for(agent.name, state)
            result: AgentRunResult = await agent.run(
                llm,
                registry,
                grounding=grounding,
                **input_builder(state),
            )
            setattr(state, target, result.output)
            self._record(state, agent, result)

        return node

    def _make_refine_node(
        self, llm: LLMClient, registry: ToolRegistry
    ) -> Callable[[RunState], Awaitable[None]]:
        async def node(state: RunState) -> None:
            if state.critique is None:
                return

            failing = state.critique.failing(settings.QUALITY_THRESHOLD)
            targets = [
                (artifact, ARTIFACT_OWNERS[artifact])
                for artifact in failing
                if artifact in ARTIFACT_OWNERS and ARTIFACT_OWNERS[artifact] in self.agents
            ]
            if not targets:
                return

            app_logger.info(
                "Refining artifacts below threshold",
                threshold=settings.QUALITY_THRESHOLD,
                artifacts=[artifact for artifact, _ in targets],
            )

            # Refine independently-owned artifacts concurrently. Only one pass:
            # unbounded critique/regenerate loops burn latency for diminishing
            # returns and can oscillate between two equally-mediocre versions.
            await asyncio.gather(
                *(self._refine_one(state, artifact, owner, llm, registry) for artifact, owner in targets),
                return_exceptions=True,
            )

        return node

    async def _refine_one(
        self,
        state: RunState,
        artifact: str,
        owner: str,
        llm: LLMClient,
        registry: ToolRegistry,
    ) -> None:
        agent = self.agents[owner]
        critique = next(
            (item for item in (state.critique.critiques if state.critique else []) if item.artifact == artifact),
            None,
        )
        if critique is None or not critique.fix_instructions:
            return

        target = self._state_attr_for(artifact)
        current = getattr(state, target, None)
        if current is None:
            return

        try:
            result: AgentRunResult = await agent.run(
                llm,
                registry,
                grounding=await self._grounding_for(agent.name, state),
                feedback=critique.fix_instructions,
                previous_attempt=current.model_dump(),
                **self._inputs_for(owner, state),
            )
        except Exception as exc:
            # Keep the original artifact: a failed revision must not lose work.
            app_logger.warning("Refinement failed, keeping original", agent=owner, error=str(exc)[:200])
            state.errors[f"refine_{owner}"] = str(exc)[:300]
            return

        setattr(state, target, result.output)
        state.refined.append(artifact)
        self._record(state, agent, result, note=f"revised after review ({critique.overall}/10)")

    # ----------------------------------------------------------- input builders

    def _planner_inputs(self, state: RunState) -> Dict[str, Any]:
        return {"idea": state.idea}

    def _analyst_inputs(self, state: RunState) -> Dict[str, Any]:
        return {"vision": state.vision, "idea": state.idea}

    def _prioritizer_inputs(self, state: RunState) -> Dict[str, Any]:
        return {"vision": state.vision}

    def _architect_inputs(self, state: RunState) -> Dict[str, Any]:
        return {"prd": state.prd}

    def _tickets_inputs(self, state: RunState) -> Dict[str, Any]:
        return {
            "prd": state.prd,
            "architecture": state.architecture,
            "features": state.priorities.features_detailed if state.priorities else None,
        }

    def _critic_inputs(self, state: RunState) -> Dict[str, Any]:
        return {"idea": state.idea, "bundle": self._review_bundle(state)}

    def _inputs_for(self, agent_name: str, state: RunState) -> Dict[str, Any]:
        builders = {
            "planner": self._planner_inputs,
            "analyst": self._analyst_inputs,
            "prioritizer": self._prioritizer_inputs,
            "architect": self._architect_inputs,
            "ticket_generator": self._tickets_inputs,
        }
        return builders[agent_name](state)

    @staticmethod
    def _state_attr_for(artifact: str) -> str:
        return {
            "plan": "vision",
            "prd": "prd",
            "features_detailed": "priorities",
            "architecture": "architecture",
            "tickets": "tickets",
        }[artifact]

    # ---------------------------------------------------------------- helpers

    async def _grounding_for(self, agent_name: str, state: RunState) -> str:
        """Domain-targeted pre-retrieval for one agent."""
        domains = GROUNDING_DOMAINS.get(agent_name)
        if not domains or not self.retriever.available:
            return state.grounding

        product = state.vision.product_name if state.vision else ""
        query = f"{' '.join(domains)} best practice for {product or state.idea}"
        result = await self.retriever.retrieve(query, k=settings.RAG_TOP_K, domains=domains)
        if result.is_empty:
            return state.grounding
        state.merge_citations(result.citations)
        return result.context

    def _record(self, state: RunState, agent: BaseAgent, result: AgentRunResult, note: str = "") -> None:
        state.usage = state.usage + result.usage
        state.merge_citations(result.citations)
        state.record_step(
            AgentStep(
                agent=agent.name,
                label=agent.label,
                model=agent.model,
                duration_seconds=round(result.duration, 2),
                tool_calls=result.tool_calls,
                citations=result.citations,
                tokens=result.usage.total_tokens,
                repairs=result.repairs,
                note=note,
            )
        )

    @staticmethod
    def _review_bundle(state: RunState) -> Dict[str, str]:
        return review_digest(
            state.vision, state.prd, state.priorities, state.architecture, state.tickets
        )

    def _persist(self, state: RunState) -> None:
        if self.memory is None or state.vision is None:
            return
        try:
            self.memory.record(
                MemoryEntry(
                    entry_id=f"{state.thread_id}:{len(state.steps)}",
                    thread_id=state.thread_id,
                    created_at=datetime.now(timezone.utc),
                    idea=state.idea,
                    product_name=state.vision.product_name,
                    problem_statement=state.vision.problem_statement,
                    quality_score=state.critique.overall_quality if state.critique else None,
                    tech_stack=list(state.architecture.tech_stack.values()) if state.architecture else [],
                    top_features=[
                        feature.name for feature in (state.priorities.features_detailed[:5] if state.priorities else [])
                    ],
                    target_users=list(state.vision.target_users),
                )
            )
        except Exception as exc:
            app_logger.warning("Could not persist run to memory", error=str(exc)[:200])

    # --------------------------------------------------------------- assembly

    def assemble(self, state: RunState) -> Dict[str, Any]:
        """Shape the final API payload."""
        payload: Dict[str, Any] = {
            "plan": state.vision.model_dump() if state.vision else None,
            "prd": state.prd.model_dump() if state.prd else None,
            "architecture": state.architecture.model_dump() if state.architecture else None,
            "tickets": state.tickets.model_dump() if state.tickets else None,
            "features_detailed": [
                feature.model_dump() for feature in (state.priorities.features_detailed if state.priorities else [])
            ],
            "sequencing_rationale": state.priorities.sequencing_rationale if state.priorities else "",
            "agent_steps": [step.model_dump() for step in state.steps],
            "citations": [citation.model_dump() for citation in state.citations],
            "quality": self._quality_payload(state),
            "meta": {
                "thread_id": state.thread_id,
                "depth": state.depth.value,
                "execution_time": state.elapsed,
                "models": {
                    "primary": settings.GROQ_MODEL,
                    "fast": settings.GROQ_FAST_MODEL,
                    "alt": settings.GROQ_ALT_MODEL,
                },
                "agent_models": {step.agent: step.model for step in state.steps if step.model},
                "prompt_tokens": state.usage.prompt_tokens,
                "completion_tokens": state.usage.completion_tokens,
                "total_tokens": state.usage.total_tokens,
                "retrieval": {
                    "enabled": self.retriever.available,
                    "retrievers": state.retrievers_used,
                    "corpus_chunks": self.retriever.store.size,
                    "dense": self.retriever.store.has_dense,
                    "sources_cited": len(state.citations),
                },
                "refined_artifacts": state.refined,
                "agents_run": [step.agent for step in state.steps],
                "errors": state.errors,
            },
        }
        return payload

    @staticmethod
    def _quality_payload(state: RunState) -> Optional[Dict[str, Any]]:
        if state.critique is None:
            return None
        return {
            "overall": state.critique.overall_quality,
            "grade": _grade(state.critique.overall_quality),
            "assessment": state.critique.overall_assessment,
            "blocking_issues": state.critique.blocking_issues,
            "threshold": settings.QUALITY_THRESHOLD,
            "artifacts": [
                {
                    "artifact": item.artifact,
                    "overall": item.overall,
                    "completeness": item.completeness,
                    "consistency": item.consistency,
                    "specificity": item.specificity,
                    "feasibility": item.feasibility,
                    "issues": item.issues,
                    "fix_instructions": item.fix_instructions,
                    "revised": item.artifact in state.refined,
                }
                for item in state.critique.critiques
            ],
        }


def _enabled(node_name: str):
    """Predicate: is this node included at the run's requested depth?"""

    def predicate(state: RunState) -> bool:
        return node_name not in DEPTH_SKIPS.get(state.depth.value, frozenset())

    return predicate


def _grade(score: float) -> str:
    for threshold, label in ((9.0, "A"), (8.0, "B+"), (7.0, "B"), (6.0, "C"), (5.0, "D")):
        if score >= threshold:
            return label
    return "F"
