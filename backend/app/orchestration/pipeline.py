"""
The product-management agent pipeline, orchestrated with LangGraph.

    START ─> retrieve ─> planner ─┬─> analyst ──> architect ─┐
                                  │                           ├─> tickets ─> critic? ─> refine? ─> END
                                  └─> prioritizer ────────────┘

`analyst` and `prioritizer` both depend only on the vision, so LangGraph runs
them in a single superstep. `tickets` has incoming edges from both `architect`
and `prioritizer`, so LangGraph joins the branches and waits for both.

Two conventions worth knowing when reading the nodes below:

* **Skipping happens inside a node, not via an edge.** `prioritizer` is part of
  a fan-in; routing around it at `quick` depth would leave `tickets` waiting on
  a branch that never arrives. A skipped node returns an empty update instead.
  The genuinely linear tail after `tickets` does use conditional edges, which is
  what they are for.
* **Non-critical nodes swallow their own failures**, recording them on the error
  channel and returning a partial update. A raising node aborts the whole graph,
  and a failed review should degrade the response to an unreviewed plan rather
  than discard five artifacts that already succeeded.

Checkpointing is real: the compiled graph carries a process-wide `MemorySaver`,
so a run is addressable by `thread_id` and its state can be read back after the
fact (see the `/threads/{thread_id}` route).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

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
from ..schemas.artifacts import AgentStep, Citation
from ..tools.base import ToolContext
from ..tools.mcp_bridge import MCPBridge
from ..tools.registry import ToolRegistry
from .state import Depth, PipelineState, dedupe_citations, initial_state

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
#: in a minute. `standard` and `deep` add agents and accept some pacing.
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

#: Nodes omitted at a given depth, to stay inside the token budget.
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

#: State key holding each artifact, keyed by its critique name.
ARTIFACT_KEYS = {
    "plan": "vision",
    "prd": "prd",
    "features_detailed": "priorities",
    "architecture": "architecture",
    "tickets": "tickets",
}

def _artifact_msgpack_allowlist() -> list:
    """Every model in app.schemas.artifacts, as the (module, qualname) pairs
    LangGraph's msgpack allowlist actually expects.

    State carries these types (ProductVision, PRD, nested ones like UserStory,
    ...) and the default serializer accepts them only permissively, with a
    per-checkpoint warning that it "will be blocked in a future version".
    Enumerating the module rather than hand-listing top-level types is what
    keeps this correct as the schema grows -- a hardcoded list silently stops
    covering new nested models the day someone adds one.
    """
    from .. import schemas

    return [
        (schemas.artifacts.__name__, name)
        for name, obj in vars(schemas.artifacts).items()
        if isinstance(obj, type) and issubclass(obj, schemas.artifacts.Artifact)
    ]


#: See _artifact_msgpack_allowlist for why this is derived rather than listed.
_SERDE = JsonPlusSerializer(allowed_msgpack_modules=_artifact_msgpack_allowlist())

#: Process-wide, so a thread's checkpoints outlive the request that created
#: them. In-memory, therefore per-instance: swap in a Postgres or Redis saver to
#: make resume survive a restart.
_CHECKPOINTER = MemorySaver(serde=_SERDE)


def get_checkpointer() -> MemorySaver:
    return _CHECKPOINTER


class ProductPlanPipeline:
    """Builds and executes the LangGraph agent graph for one product idea."""

    def __init__(self, retriever: Optional[Retriever] = None):
        self.retriever = retriever or Retriever()
        self.memory = get_memory() if settings.MEMORY_ENABLED else None

        self.planner = PlannerAgent()
        self.analyst = AnalystAgent()
        self.prioritizer = PrioritizerAgent()
        self.architect = ArchitectAgent()
        self.ticket_generator = TicketGeneratorAgent()
        self.critic = CriticAgent()

        #: Agents that own a regenerable artifact. The critic is excluded: it
        #: reviews artifacts rather than producing one.
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
        thread = thread_id or f"thread_{uuid.uuid4().hex[:12]}"

        for name, role in DEPTH_MODEL_ROLES.get(depth.value, {}).items():
            agent = self.agents.get(name) or (self.critic if name == "critic" else None)
            if agent is not None:
                agent.model_role = role

        started = datetime.now(timezone.utc)

        async with LLMClient() as llm, MCPBridge() as bridge:
            registry = ToolRegistry(
                ToolContext(retriever=self.retriever, memory=self.memory, thread_id=thread)
            )
            if bridge.tools:
                registry.register_many(bridge.tools)
                # External tools go to the ticket agent, which is the one with a
                # reason to reach outside: filing the work it just wrote.
                self.ticket_generator.tool_names = tuple(
                    [*self.ticket_generator.tool_names, *(tool.name for tool in bridge.tools)]
                )

            graph = self.build_graph(llm, registry, on_event)
            app_logger.info(
                "Executing LangGraph pipeline",
                thread_id=thread,
                depth=depth.value,
                nodes=sorted(graph.get_graph().nodes),
                tools=registry.names,
            )

            final: PipelineState = await graph.ainvoke(
                initial_state(idea.strip(), thread, depth),
                config={"configurable": {"thread_id": thread}, "recursion_limit": 25},
            )

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        self._persist(final)
        return self.assemble(final, elapsed)

    # ------------------------------------------------------------------ graph

    def build_graph(
        self,
        llm: Optional[LLMClient] = None,
        registry: Optional[ToolRegistry] = None,
        on_event: EventSink = None,
    ):
        """Compile the StateGraph.

        `llm` and `registry` are captured by the node closures but never called
        during construction, so passing None yields a graph valid for topology
        introspection.
        """
        workflow = StateGraph(PipelineState)

        workflow.add_node("retrieve", self._node_retrieve(on_event))
        workflow.add_node(
            "planner",
            self._agent_node(self.planner, llm, registry, on_event, self._planner_inputs, "vision"),
        )
        workflow.add_node(
            "analyst",
            self._agent_node(self.analyst, llm, registry, on_event, self._analyst_inputs, "prd"),
        )
        workflow.add_node(
            "prioritizer",
            self._agent_node(
                self.prioritizer,
                llm,
                registry,
                on_event,
                self._prioritizer_inputs,
                "priorities",
                critical=False,
            ),
        )
        workflow.add_node(
            "architect",
            self._agent_node(
                self.architect, llm, registry, on_event, self._architect_inputs, "architecture"
            ),
        )
        workflow.add_node(
            "ticket_generator",
            self._agent_node(
                self.ticket_generator, llm, registry, on_event, self._tickets_inputs, "tickets"
            ),
        )
        workflow.add_node(
            "critic",
            self._agent_node(
                self.critic, llm, registry, on_event, self._critic_inputs, "critique", critical=False
            ),
        )
        workflow.add_node("refine", self._node_refine(llm, registry, on_event))

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "planner")

        # Fan-out: one superstep runs both branches.
        workflow.add_edge("planner", "analyst")
        workflow.add_edge("planner", "prioritizer")

        # Fan-in on `architect`, not on `ticket_generator`.
        #
        # This matters more than it looks. LangGraph schedules a node whenever an
        # incoming channel is written, so a join only executes once if every
        # inbound branch lands in the *same* superstep. Joining the two branches
        # at `ticket_generator` would put `prioritizer` (one hop from planner) and
        # `architect` (two hops) at different depths, and the node would run twice
        # -- the first time with `architecture` still None.
        #
        # `analyst` and `prioritizer` are both one hop from `planner`, so joining
        # here is depth-balanced and fires exactly once. The architect does not
        # read the prioritized list; the edge exists to make the join correct.
        workflow.add_edge("analyst", "architect")
        workflow.add_edge("prioritizer", "architect")

        workflow.add_edge("architect", "ticket_generator")

        # The tail is linear, so conditional edges skip nodes outright rather
        # than running them as no-ops.
        workflow.add_conditional_edges(
            "ticket_generator", self._route_after_tickets, {"critic": "critic", "end": END}
        )
        workflow.add_conditional_edges(
            "critic", self._route_after_critic, {"refine": "refine", "end": END}
        )
        workflow.add_edge("refine", END)

        return workflow.compile(checkpointer=_CHECKPOINTER)

    # ----------------------------------------------------------------- routes

    @staticmethod
    def _route_after_tickets(state: PipelineState) -> str:
        skips = DEPTH_SKIPS.get(state.get("depth", "standard"), frozenset())
        return "end" if "critic" in skips else "critic"

    @staticmethod
    def _route_after_critic(state: PipelineState) -> str:
        skips = DEPTH_SKIPS.get(state.get("depth", "standard"), frozenset())
        critique = state.get("critique")
        if "refine" in skips or critique is None:
            return "end"
        return "refine" if critique.failing(settings.QUALITY_THRESHOLD) else "end"

    # ------------------------------------------------------------------ nodes

    def _node_retrieve(self, on_event: EventSink):
        label = "Retrieving domain knowledge"

        async def retrieve(state: PipelineState) -> Dict[str, Any]:
            """Pre-fetch shared grounding. No LLM call."""
            await _emit(on_event, {"type": "node_start", "node": "retrieve", "label": label})

            if not self.retriever.available:
                await _emit(
                    on_event, {"type": "node_end", "node": "retrieve", "label": label, "duration": 0.0}
                )
                return {}

            result = await self.retriever.retrieve(
                f"product discovery problem framing target users for: {state['idea']}",
                k=settings.RAG_TOP_K,
            )
            note = (
                f"{len(result.chunks)} passages via {', '.join(result.retrievers_used) or 'none'}"
                if result.chunks
                else "knowledge base unavailable"
            )
            await _emit(
                on_event, {"type": "node_end", "node": "retrieve", "label": label, "duration": 0.0}
            )
            return {
                "grounding": result.context,
                "retrievers_used": result.retrievers_used,
                "citations": result.citations,
                "steps": [
                    AgentStep(
                        agent="retrieve",
                        label=label,
                        duration_seconds=0.0,
                        citations=result.citations,
                        note=note,
                    )
                ],
            }

        return retrieve

    def _agent_node(
        self,
        agent: BaseAgent,
        llm: Optional[LLMClient],
        registry: Optional[ToolRegistry],
        on_event: EventSink,
        input_builder: Callable[[PipelineState], Dict[str, Any]],
        target: str,
        *,
        critical: bool = True,
    ):
        async def node(state: PipelineState) -> Dict[str, Any]:
            if agent.name in DEPTH_SKIPS.get(state.get("depth", "standard"), frozenset()):
                await _emit(
                    on_event, {"type": "node_skipped", "node": agent.name, "label": agent.label}
                )
                return {}

            await _emit(on_event, {"type": "node_start", "node": agent.name, "label": agent.label})

            try:
                grounding, extra_citations = await self._grounding_for(agent.name, state)
                result: AgentRunResult = await agent.run(
                    llm,
                    registry,
                    grounding=grounding,
                    on_event=on_event,
                    **input_builder(state),
                )
            except Exception as exc:
                message = str(exc)
                app_logger.error(
                    "Agent node failed", node=agent.name, critical=critical, error=message[:400]
                )
                await _emit(
                    on_event,
                    {
                        "type": "node_failed",
                        "node": agent.name,
                        "label": agent.label,
                        "critical": critical,
                        "error": message[:400],
                    },
                )
                if critical:
                    # Propagate: LangGraph aborts the run, which is correct when
                    # a required artifact is missing.
                    raise
                return {"errors": {agent.name: message[:400]}}

            await _emit(
                on_event,
                {
                    "type": "node_end",
                    "node": agent.name,
                    "label": agent.label,
                    "duration": round(result.duration, 3),
                },
            )
            return {
                target: result.output,
                "steps": [
                    AgentStep(
                        agent=agent.name,
                        label=agent.label,
                        model=agent.model,
                        duration_seconds=round(result.duration, 2),
                        tool_calls=result.tool_calls,
                        citations=result.citations,
                        tokens=result.usage.total_tokens,
                        repairs=result.repairs,
                    )
                ],
                "citations": [*result.citations, *extra_citations],
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
            }

        return node

    def _node_refine(
        self, llm: Optional[LLMClient], registry: Optional[ToolRegistry], on_event: EventSink
    ):
        label = "Revising weak artifacts"

        async def refine(state: PipelineState) -> Dict[str, Any]:
            critique = state.get("critique")
            if critique is None:
                return {}

            targets = [
                (artifact, ARTIFACT_OWNERS[artifact])
                for artifact in critique.failing(settings.QUALITY_THRESHOLD)
                if artifact in ARTIFACT_OWNERS and ARTIFACT_OWNERS[artifact] in self.agents
            ]
            if not targets:
                return {}

            await _emit(on_event, {"type": "node_start", "node": "refine", "label": label})
            app_logger.info(
                "Refining artifacts below threshold",
                threshold=settings.QUALITY_THRESHOLD,
                artifacts=[artifact for artifact, _ in targets],
            )

            # Independently-owned artifacts refine concurrently. One pass only:
            # unbounded critique/regenerate loops burn latency for diminishing
            # returns and can oscillate between equally mediocre versions.
            outcomes = await asyncio.gather(
                *(
                    self._refine_one(state, artifact, owner, llm, registry, on_event)
                    for artifact, owner in targets
                ),
                return_exceptions=True,
            )

            update: Dict[str, Any] = {
                "steps": [],
                "citations": [],
                "refined": [],
                "errors": {},
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            for outcome in outcomes:
                if isinstance(outcome, BaseException) or not outcome:
                    continue
                for key, value in outcome.items():
                    if key in ("steps", "citations", "refined"):
                        update[key] = [*update[key], *value]
                    elif key in ("prompt_tokens", "completion_tokens"):
                        update[key] += value
                    elif key == "errors":
                        update["errors"] = {**update["errors"], **value}
                    else:
                        update[key] = value

            await _emit(
                on_event, {"type": "node_end", "node": "refine", "label": label, "duration": 0.0}
            )
            return update

        return refine

    async def _refine_one(
        self,
        state: PipelineState,
        artifact: str,
        owner: str,
        llm: Optional[LLMClient],
        registry: Optional[ToolRegistry],
        on_event: EventSink,
    ) -> Dict[str, Any]:
        agent = self.agents[owner]
        critique = state.get("critique")
        entry = next(
            (item for item in (critique.critiques if critique else []) if item.artifact == artifact),
            None,
        )
        if entry is None or not entry.fix_instructions:
            return {}

        key = ARTIFACT_KEYS[artifact]
        current = state.get(key)
        if current is None:
            return {}

        try:
            grounding, extra_citations = await self._grounding_for(agent.name, state)
            result: AgentRunResult = await agent.run(
                llm,
                registry,
                grounding=grounding,
                feedback=entry.fix_instructions,
                previous_attempt=current.model_dump(),
                on_event=on_event,
                **self._inputs_for(owner, state),
            )
        except Exception as exc:
            # Keep the original artifact: a failed revision must not lose work.
            app_logger.warning(
                "Refinement failed, keeping original", agent=owner, error=str(exc)[:200]
            )
            return {"errors": {f"refine_{owner}": str(exc)[:300]}}

        return {
            key: result.output,
            "refined": [artifact],
            "steps": [
                AgentStep(
                    agent=agent.name,
                    label=agent.label,
                    model=agent.model,
                    duration_seconds=round(result.duration, 2),
                    tool_calls=result.tool_calls,
                    citations=result.citations,
                    tokens=result.usage.total_tokens,
                    repairs=result.repairs,
                    note=f"revised after review ({entry.overall}/10)",
                )
            ],
            "citations": [*result.citations, *extra_citations],
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
        }

    # ---------------------------------------------------------- input builders

    @staticmethod
    def _planner_inputs(state: PipelineState) -> Dict[str, Any]:
        return {"idea": state["idea"]}

    @staticmethod
    def _analyst_inputs(state: PipelineState) -> Dict[str, Any]:
        return {"vision": state.get("vision"), "idea": state["idea"]}

    @staticmethod
    def _prioritizer_inputs(state: PipelineState) -> Dict[str, Any]:
        return {"vision": state.get("vision")}

    @staticmethod
    def _architect_inputs(state: PipelineState) -> Dict[str, Any]:
        return {"prd": state.get("prd")}

    @staticmethod
    def _tickets_inputs(state: PipelineState) -> Dict[str, Any]:
        priorities = state.get("priorities")
        return {
            "prd": state.get("prd"),
            "architecture": state.get("architecture"),
            "features": priorities.features_detailed if priorities else None,
        }

    @staticmethod
    def _critic_inputs(state: PipelineState) -> Dict[str, Any]:
        return {
            "idea": state["idea"],
            "bundle": review_digest(
                state.get("vision"),
                state.get("prd"),
                state.get("priorities"),
                state.get("architecture"),
                state.get("tickets"),
            ),
        }

    def _inputs_for(self, agent_name: str, state: PipelineState) -> Dict[str, Any]:
        return {
            "planner": self._planner_inputs,
            "analyst": self._analyst_inputs,
            "prioritizer": self._prioritizer_inputs,
            "architect": self._architect_inputs,
            "ticket_generator": self._tickets_inputs,
        }[agent_name](state)

    # ---------------------------------------------------------------- helpers

    async def _grounding_for(
        self, agent_name: str, state: PipelineState
    ) -> Tuple[str, List[Citation]]:
        """Domain-targeted pre-retrieval for one agent."""
        domains = GROUNDING_DOMAINS.get(agent_name)
        if not domains or not self.retriever.available:
            return state.get("grounding", ""), []

        vision = state.get("vision")
        subject = vision.product_name if vision else state["idea"]
        result = await self.retriever.retrieve(
            f"{' '.join(domains)} best practice for {subject}",
            k=settings.RAG_TOP_K,
            domains=domains,
        )
        if result.is_empty:
            return state.get("grounding", ""), []
        return result.context, result.citations

    def _persist(self, state: PipelineState) -> None:
        vision = state.get("vision")
        if self.memory is None or vision is None:
            return
        try:
            priorities = state.get("priorities")
            architecture = state.get("architecture")
            critique = state.get("critique")
            self.memory.record(
                MemoryEntry(
                    entry_id=f"{state['thread_id']}:{len(state.get('steps') or [])}",
                    thread_id=state["thread_id"],
                    created_at=datetime.now(timezone.utc),
                    idea=state["idea"],
                    product_name=vision.product_name,
                    problem_statement=vision.problem_statement,
                    quality_score=critique.overall_quality if critique else None,
                    tech_stack=list(architecture.tech_stack.values()) if architecture else [],
                    top_features=[
                        f.name for f in (priorities.features_detailed[:5] if priorities else [])
                    ],
                    target_users=list(vision.target_users),
                )
            )
        except Exception as exc:
            app_logger.warning("Could not persist run to memory", error=str(exc)[:200])

    # --------------------------------------------------------------- assembly

    def assemble(self, state: PipelineState, elapsed: float) -> Dict[str, Any]:
        """Shape the final API payload."""
        vision = state.get("vision")
        prd = state.get("prd")
        priorities = state.get("priorities")
        architecture = state.get("architecture")
        tickets = state.get("tickets")
        steps = state.get("steps") or []
        citations = dedupe_citations(state.get("citations") or [])

        prompt_tokens = state.get("prompt_tokens", 0)
        completion_tokens = state.get("completion_tokens", 0)

        return {
            "plan": vision.model_dump() if vision else None,
            "prd": prd.model_dump() if prd else None,
            "architecture": architecture.model_dump() if architecture else None,
            "tickets": tickets.model_dump() if tickets else None,
            "features_detailed": [
                feature.model_dump()
                for feature in (priorities.features_detailed if priorities else [])
            ],
            "sequencing_rationale": priorities.sequencing_rationale if priorities else "",
            "agent_steps": [step.model_dump() for step in steps],
            "citations": [citation.model_dump() for citation in citations],
            "quality": self._quality_payload(state),
            "meta": {
                "thread_id": state["thread_id"],
                "depth": state.get("depth", "standard"),
                "execution_time": round(elapsed, 3),
                "orchestrator": "langgraph",
                "models": {
                    "primary": settings.GROQ_MODEL,
                    "fast": settings.GROQ_FAST_MODEL,
                    "alt": settings.GROQ_ALT_MODEL,
                },
                "agent_models": {step.agent: step.model for step in steps if step.model},
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "retrieval": {
                    "enabled": self.retriever.available,
                    "retrievers": state.get("retrievers_used") or [],
                    "corpus_chunks": self.retriever.store.size,
                    "dense": self.retriever.store.has_dense,
                    "sources_cited": len(citations),
                },
                "refined_artifacts": state.get("refined") or [],
                "agents_run": [step.agent for step in steps],
                "errors": state.get("errors") or {},
            },
        }

    @staticmethod
    def _quality_payload(state: PipelineState) -> Optional[Dict[str, Any]]:
        critique = state.get("critique")
        if critique is None:
            return None
        refined = state.get("refined") or []
        return {
            "overall": critique.overall_quality,
            "grade": _grade(critique.overall_quality),
            "assessment": critique.overall_assessment,
            "blocking_issues": critique.blocking_issues,
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
                    "revised": item.artifact in refined,
                }
                for item in critique.critiques
            ],
        }


async def _emit(sink: EventSink, event: Dict[str, Any]) -> None:
    if sink is None:
        return
    try:
        await sink(event)
    except Exception as exc:
        app_logger.warning("Event sink raised", error=str(exc)[:200])


def _grade(score: float) -> str:
    for threshold, label in ((9.0, "A"), (8.0, "B+"), (7.0, "B"), (6.0, "C"), (5.0, "D")):
        if score >= threshold:
            return label
    return "F"
