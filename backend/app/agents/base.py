"""
Agent base class.

Every agent runs the same two-phase loop:

1. **Research** -- the model is given its tools and may call them (up to
   `MAX_TOOL_ITERATIONS` rounds) to gather grounding from the knowledge base,
   compute scores, or recall prior work. Tool calls in one round execute
   concurrently.
2. **Emit** -- tools are withdrawn, JSON mode is switched on, and the model is
   asked for exactly the target schema. The result is validated with Pydantic;
   on failure the specific field errors are fed back as a repair prompt and the
   model tries again, up to `MAX_REPAIR_ATTEMPTS`.

Splitting the phases matters: when tools and a final answer are both available
in one call, models routinely emit another tool call where the answer belongs,
and JSON mode cannot be enabled at the same time as tool calling on most
providers.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Sequence, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from ..llm.client import LLMClient, LLMResponse, Usage
from ..llm.errors import LLMBadRequestError
from ..schemas.artifacts import Citation
from ..tools.registry import ToolRegistry
from .structured import extract_json_object, format_validation_errors, render_schema

T = TypeVar("T", bound=BaseModel)

EventSink = Any  # Callable[[dict], Awaitable[None]] | None


@dataclass
class AgentRunResult(Generic[T]):
    output: T
    citations: List[Citation] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    duration: float = 0.0
    repairs: int = 0
    tool_data: Dict[str, Any] = field(default_factory=dict)


class AgentFailure(RuntimeError):
    """The agent could not produce a schema-valid artifact."""

    def __init__(self, agent: str, message: str):
        super().__init__(f"{agent}: {message}")
        self.agent = agent


#: Provider token budgets are enforced per model, so a role is really a choice
#: of *which budget to spend*. Assigning consecutive or concurrent agents to
#: different roles is what keeps a run from stalling on a single 8k/min ceiling.
ModelRole = str  # "primary" | "fast" | "alt"


def resolve_model(role: ModelRole) -> str:
    return {
        "primary": settings.GROQ_MODEL,
        "fast": settings.GROQ_FAST_MODEL,
        "alt": settings.GROQ_ALT_MODEL,
    }.get(role, settings.GROQ_MODEL)


class BaseAgent(ABC, Generic[T]):
    name: str = "agent"
    label: str = "Agent"
    output_model: Type[BaseModel]
    tool_names: Tuple[str, ...] = ()
    temperature: float = 0.4
    max_tokens: int = 2600
    model_role: ModelRole = "primary"
    max_tool_iterations: Optional[int] = None

    @property
    def model(self) -> str:
        return resolve_model(self.model_role)

    # ----------------------------------------------------------- subclass API

    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's role, standards, and constraints."""

    @abstractmethod
    def build_task(self, **inputs: Any) -> str:
        """The concrete request, rendered from upstream artifacts."""

    def research_directive(self) -> str:
        """Guidance for the tool phase. Empty when the agent has no tools."""
        if not self.tool_names:
            return ""
        return (
            "First, gather what you need. Call the tools available to you to ground "
            "your decisions in established practice before answering. When you have "
            "enough, reply with a short plain-text summary of your findings and stop "
            "calling tools."
        )

    # --------------------------------------------------------------- execution

    async def run(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        *,
        grounding: str = "",
        feedback: Optional[Sequence[str]] = None,
        previous_attempt: Optional[Dict[str, Any]] = None,
        on_event: EventSink = None,
        **inputs: Any,
    ) -> AgentRunResult[T]:
        started = time.perf_counter()
        usage = Usage()
        citations: List[Citation] = []
        called_tools: List[str] = []
        tool_data: Dict[str, Any] = {}

        task_message = self._compose_user_message(grounding, feedback, previous_attempt, **inputs)
        model = self.model
        findings: List[str] = []

        # -------------------------------------------------- phase 1: research
        if self.tool_names:
            research: List[Dict[str, Any]] = [
                {"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": task_message},
            ]
            schemas = registry.schemas(self.tool_names)
            max_rounds = self.max_tool_iterations or settings.MAX_TOOL_ITERATIONS

            for round_index in range(max_rounds):
                try:
                    response = await llm.complete(
                        research,
                        model=model,
                        tools=schemas,
                        temperature=self.temperature,
                        max_tokens=700,
                    )
                except LLMBadRequestError as exc:
                    # Groq validates tool arguments server-side, so a malformed
                    # call (commonly empty `arguments`) fails the whole request
                    # rather than arriving as a call this code could reject.
                    # Research is an enhancement, not a precondition: abandon it
                    # and emit from what is already known. Correctness does not
                    # depend on it -- anything that must be exact, like RICE
                    # arithmetic, is recomputed in postprocess regardless.
                    if "tool_use_failed" not in str(exc):
                        raise
                    app_logger.warning(
                        "Tool call was malformed; continuing without research",
                        agent=self.name,
                        error=str(exc)[:200],
                    )
                    await _emit(
                        on_event,
                        {"type": "tool_failed", "agent": self.name, "error": str(exc)[:200]},
                    )
                    break

                usage = usage + response.usage

                if not response.tool_calls:
                    if response.content:
                        findings.append(response.content.strip())
                    break

                research.append(response.raw_message)
                executed = await registry.execute_all(response.tool_calls)

                for call, result in executed:
                    called_tools.append(call.name)
                    citations.extend(result.citations)
                    tool_data.update(result.data)
                    research.append(ToolRegistry.to_tool_message(call.id, result))
                    findings.append(f"Result of {call.name}:\n{result.content}")
                    await _emit(
                        on_event,
                        {
                            "type": "tool_call",
                            "agent": self.name,
                            "tool": call.name,
                            "ok": result.ok,
                            "round": round_index + 1,
                            "summary": _summarize_args(call.arguments),
                        },
                    )

        # ----------------------------------------------------- phase 2: emit
        #
        # Built fresh rather than continued from the research transcript. A model
        # that has just made a successful tool call will keep making them --
        # withdrawing the `tools` parameter is not enough when the schema and a
        # worked example are still sitting in its context, and the provider
        # rejects a tool call once tool_choice is none. Carrying the findings
        # forward as plain text removes the pattern to imitate, and drops the
        # tool-call scaffolding from the token count too.
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": task_message},
        ]
        if findings:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "## What your research returned\n\n"
                        "Treat these as authoritative and use them verbatim where they give "
                        "computed values.\n\n" + "\n\n".join(findings)[:8000]
                    ),
                }
            )
        messages.append({"role": "user", "content": self._emit_instruction()})

        last_error = ""
        for attempt in range(settings.MAX_REPAIR_ATTEMPTS + 1):
            # The provider call belongs inside the try: a rejected request
            # (a stray tool call, an unvalidatable JSON body) is as recoverable
            # as a schema violation, and both belong in the same repair loop.
            response: Optional[LLMResponse] = None
            try:
                response = await llm.complete(
                    messages,
                    model=model,
                    temperature=self.temperature if attempt == 0 else min(0.2, self.temperature),
                    max_tokens=self.max_tokens,
                    json_mode=True,
                )
                usage = usage + response.usage

                payload = extract_json_object(response.content)
                validated = self.output_model.model_validate(payload)
                output = self.postprocess(validated, tool_data)
                return AgentRunResult(
                    output=output,  # type: ignore[arg-type]
                    citations=_dedupe_citations(citations),
                    tool_calls=called_tools,
                    usage=usage,
                    duration=time.perf_counter() - started,
                    repairs=attempt,
                    tool_data=tool_data,
                )
            except ValidationError as exc:
                last_error = format_validation_errors(exc)
                if response is not None and response.finish_reason == "length":
                    # Distinguish "wrong" from "cut off". Telling a model to fix
                    # field errors when it actually ran out of room produces the
                    # same overlong answer again.
                    last_error = (
                        "- Your response was cut off before it finished, so the object is "
                        "incomplete. Produce the same structure but more concisely: fewer "
                        "list items, shorter descriptions.\n" + last_error
                    )
            except LLMBadRequestError as exc:
                # The emit phase withholds tools, but a model fresh from a tool
                # round sometimes emits another call anyway; Groq rejects that
                # with `tool_use_failed`. Same for a JSON-mode body the provider
                # cannot validate. Both are recoverable by restating the ask, so
                # they rejoin the repair loop instead of aborting the agent.
                message = str(exc)
                if "tool_use_failed" in message:
                    last_error = (
                        "- You emitted a tool call. Tools are no longer available in this "
                        "phase; answer with the JSON object itself."
                    )
                elif "json_validate_failed" in message or "response_format" in message:
                    last_error = "- The response was not a single valid JSON object."
                else:
                    raise
            except ValueError as exc:
                last_error = f"- {exc}"

            if attempt == settings.MAX_REPAIR_ATTEMPTS:
                break

            app_logger.warning(
                "Agent output failed validation, requesting repair",
                agent=self.name,
                attempt=attempt + 1,
                errors=last_error[:400],
            )
            await _emit(
                on_event,
                {"type": "repair", "agent": self.name, "attempt": attempt + 1, "errors": last_error[:400]},
            )
            if response is not None and response.content:
                messages.append({"role": "assistant", "content": response.content[:4000]})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "That response does not satisfy the schema. Fix exactly these problems:\n\n"
                        f"{last_error}\n\n"
                        "Return the complete corrected JSON object. Keep everything that was already "
                        "valid, change only what the errors call out, and emit no prose."
                    ),
                }
            )

        raise AgentFailure(
            self.name,
            f"output failed schema validation after {settings.MAX_REPAIR_ATTEMPTS + 1} attempts. "
            f"Last errors:\n{last_error}",
        )

    # ----------------------------------------------------------------- hooks

    def postprocess(self, output: Any, tool_data: Dict[str, Any]) -> Any:
        """Reconcile model output with authoritative tool results."""
        return output

    # ------------------------------------------------------------- internals

    def _compose_user_message(
        self,
        grounding: str,
        feedback: Optional[Sequence[str]],
        previous_attempt: Optional[Dict[str, Any]],
        **inputs: Any,
    ) -> str:
        sections = [self.build_task(**inputs)]

        if grounding:
            sections.append(
                "## Reference material from the knowledge base\n\n"
                "Cite these with their [S#] markers where they inform a decision.\n\n"
                f"{grounding}"
            )
        if previous_attempt:
            sections.append(
                "## Your previous attempt\n\n"
                "```json\n" + _truncate_json(previous_attempt) + "\n```"
            )
        if feedback:
            bullets = "\n".join(f"- {item}" for item in feedback)
            sections.append(
                "## Required revisions\n\n"
                "A reviewer rejected the previous attempt. Address every point:\n\n"
                f"{bullets}"
            )
        if self.research_directive():
            sections.append(f"## How to work\n\n{self.research_directive()}")

        return "\n\n".join(sections)

    def _emit_instruction(self) -> str:
        return (
            "Now produce your final answer as a single JSON object conforming to this schema:\n\n"
            f"```json\n{render_schema(self.output_model)}\n```\n\n"
            "Rules:\n"
            "- Output raw JSON only. No markdown fences, no commentary.\n"
            "- Do not call any tools. This phase produces the answer itself.\n"
            "- Respect every stated minimum and maximum on arrays and numbers.\n"
            "- Be concrete and specific to this product. Generic filler is a failure.\n"
            "- Never invent a metric, number, or dependency you cannot justify."
        )


async def _emit(sink: EventSink, event: Dict[str, Any]) -> None:
    if sink is None:
        return
    try:
        await sink(event)
    except Exception as exc:
        app_logger.warning("Event sink raised", error=str(exc)[:200])


def _dedupe_citations(citations: Sequence[Citation]) -> List[Citation]:
    """Collapse repeated retrievals and renumber markers sequentially."""
    seen: Dict[str, Citation] = {}
    for citation in citations:
        key = f"{citation.doc_id}|{citation.heading}"
        if key not in seen or citation.score > seen[key].score:
            seen[key] = citation

    ordered = sorted(seen.values(), key=lambda item: item.score, reverse=True)
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


def _summarize_args(arguments: Dict[str, Any]) -> str:
    if "query" in arguments:
        return str(arguments["query"])[:120]
    if "features" in arguments and isinstance(arguments["features"], list):
        return f"{len(arguments['features'])} features"
    return ", ".join(list(arguments)[:3])


def _truncate_json(payload: Dict[str, Any], limit: int = 3500) -> str:
    import json

    blob = json.dumps(payload, indent=2, default=str)
    return blob if len(blob) <= limit else blob[:limit] + "\n… (truncated)"
