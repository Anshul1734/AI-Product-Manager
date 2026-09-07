"""
Tool registry: schema exposure and guarded dispatch.

Tool failures are converted into `ToolResult.error(...)` strings that go back to
the model as a tool message. That is deliberate -- a model that receives "ERROR:
query is required" can correct itself on the next turn, whereas raising would
abort an otherwise recoverable run.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Iterable, List, Optional

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from .base import Tool, ToolContext, ToolResult
from .knowledge import search_pm_knowledge
from .memory import recall_similar_plans
from .scoring import score_features_rice

BUILTIN_TOOLS: tuple[Tool, ...] = (
    search_pm_knowledge,
    score_features_rice,
    recall_similar_plans,
)


class ToolRegistry:
    def __init__(self, context: Optional[ToolContext] = None, tools: Optional[Iterable[Tool]] = None):
        self.context = context or ToolContext()
        self._tools: Dict[str, Tool] = {tool.name: tool for tool in (tools or BUILTIN_TOOLS)}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    @property
    def names(self) -> List[str]:
        return sorted(self._tools)

    def schemas(self, names: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """Function-calling schemas, optionally restricted to a subset."""
        if names is None:
            selected = self._tools.values()
        else:
            wanted = list(names)
            missing = [name for name in wanted if name not in self._tools]
            if missing:
                app_logger.warning("Agent requested unknown tools", tools=missing)
            selected = [self._tools[name] for name in wanted if name in self._tools]
        return [tool.schema() for tool in selected]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.error(
                f"Unknown tool '{name}'. Available tools: {', '.join(self.names)}"
            )
        if "__malformed_arguments__" in arguments:
            return ToolResult.error(
                "Arguments were not valid JSON. Re-issue the call with a well-formed JSON object."
            )

        try:
            return await asyncio.wait_for(
                tool.handler(arguments, self.context),
                timeout=settings.MCP_TOOL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            app_logger.warning("Tool timed out", tool=name, timeout=settings.MCP_TOOL_TIMEOUT)
            return ToolResult.error(f"Tool '{name}' timed out after {settings.MCP_TOOL_TIMEOUT}s")
        except Exception as exc:
            app_logger.error("Tool raised", tool=name, error=str(exc)[:300])
            return ToolResult.error(f"Tool '{name}' failed: {str(exc)[:200]}")

    async def execute_all(self, calls: List[Any]) -> List[tuple[Any, ToolResult]]:
        """Run a batch of tool calls concurrently, preserving order."""
        results = await asyncio.gather(
            *(self.execute(call.name, call.arguments) for call in calls)
        )
        return list(zip(calls, results))

    @staticmethod
    def to_tool_message(call_id: str, result: ToolResult) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "content": result.content
            if isinstance(result.content, str)
            else json.dumps(result.content),
        }
