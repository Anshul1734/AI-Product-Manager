"""
A small directed-acyclic execution engine for agent graphs.

Nodes declare their dependencies; the engine derives topological layers and runs
each layer concurrently, so independent agents (the PRD and the prioritized
feature list, which both derive only from the vision) overlap instead of
queueing. A `when` predicate skips nodes that the requested depth does not
need, and non-critical nodes may fail without aborting the run.

This is deliberately ~120 lines rather than a LangGraph dependency: the project
needs fan-out, conditional skips, and one bounded refine pass, all of which fit
in a DAG plus an explicit loop node. Pulling in a graph framework would add
tens of megabytes to a serverless bundle -- and an earlier attempt at exactly
that is what left this repo with an uninstallable import chain.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from ..core.logging.logger import app_logger

NodeRunner = Callable[[Any], Awaitable[None]]
Predicate = Callable[[Any], bool]
EventSink = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


class GraphError(RuntimeError):
    """A critical node failed; the run cannot produce a usable result."""


@dataclass
class Node:
    name: str
    label: str
    run: NodeRunner
    #: Hard edges. If one of these is skipped or fails, this node cannot run.
    depends_on: Sequence[str] = field(default_factory=tuple)
    #: Ordering-only edges. This node runs after them, but tolerates their
    #: absence -- used where an optional input degrades quality without
    #: making the step impossible.
    after: Sequence[str] = field(default_factory=tuple)
    when: Optional[Predicate] = None
    critical: bool = True

    @property
    def all_edges(self) -> List[str]:
        return [*self.depends_on, *self.after]


class Graph:
    def __init__(self, nodes: Sequence[Node]):
        self.nodes: Dict[str, Node] = {node.name: node for node in nodes}
        self._layers = self._topological_layers()

    def _topological_layers(self) -> List[List[Node]]:
        """Group nodes into waves that can each run concurrently."""
        remaining = dict(self.nodes)
        satisfied: set[str] = set()
        layers: List[List[Node]] = []

        for node in self.nodes.values():
            unknown = [dep for dep in node.all_edges if dep not in self.nodes]
            if unknown:
                raise GraphError(f"Node '{node.name}' depends on undefined node(s): {unknown}")

        while remaining:
            ready = [
                node
                for node in remaining.values()
                if all(dep in satisfied for dep in node.all_edges)
            ]
            if not ready:
                raise GraphError(f"Cycle detected among nodes: {sorted(remaining)}")
            layers.append(ready)
            for node in ready:
                satisfied.add(node.name)
                remaining.pop(node.name)
        return layers

    def describe(self) -> List[List[str]]:
        return [[node.name for node in layer] for layer in self._layers]

    async def run(self, state: Any, on_event: EventSink = None) -> Any:
        skipped: set[str] = set()

        for layer in self._layers:
            runnable: List[Node] = []
            for node in layer:
                # A node whose dependency was skipped or failed cannot run.
                blocked = [dep for dep in node.depends_on if dep in skipped]
                if blocked:
                    skipped.add(node.name)
                    continue
                if node.when is not None and not node.when(state):
                    skipped.add(node.name)
                    await _emit(on_event, {"type": "node_skipped", "node": node.name, "label": node.label})
                    continue
                runnable.append(node)

            if not runnable:
                continue

            results = await asyncio.gather(
                *(self._run_node(node, state, on_event) for node in runnable),
                return_exceptions=True,
            )

            for node, result in zip(runnable, results):
                if not isinstance(result, BaseException):
                    continue
                if isinstance(result, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                    raise result

                message = str(result)
                state.errors[node.name] = message
                skipped.add(node.name)
                app_logger.error("Graph node failed", node=node.name, critical=node.critical, error=message[:400])
                await _emit(
                    on_event,
                    {
                        "type": "node_failed",
                        "node": node.name,
                        "label": node.label,
                        "critical": node.critical,
                        "error": message[:400],
                    },
                )
                if node.critical:
                    raise GraphError(f"Required step '{node.label}' failed: {message}") from result

        return state

    @staticmethod
    async def _run_node(node: Node, state: Any, on_event: EventSink) -> None:
        await _emit(on_event, {"type": "node_start", "node": node.name, "label": node.label})
        started = time.perf_counter()
        await node.run(state)
        await _emit(
            on_event,
            {
                "type": "node_end",
                "node": node.name,
                "label": node.label,
                "duration": round(time.perf_counter() - started, 3),
            },
        )


async def _emit(sink: EventSink, event: Dict[str, Any]) -> None:
    if sink is None:
        return
    try:
        await sink(event)
    except Exception as exc:
        app_logger.warning("Event sink raised", error=str(exc)[:200])
