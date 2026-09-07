"""
MCP client bridge: expose tools from external Model Context Protocol servers to
the agent pipeline.

This is how the pipeline reaches systems it does not own -- a Linear or Jira MCP
server to file the tickets it just wrote, a Notion server to publish the PRD, a
Postgres server to check a real schema before the architect proposes one.
Discovered MCP tools are adapted into the same `Tool` shape as built-ins, so
agents call them through ordinary function calling and need no MCP awareness.

Disabled unless `MCP_SERVERS` is configured, and skipped entirely on serverless
where spawning stdio subprocesses per request is not viable. The `mcp` package
is imported lazily so the serverless bundle does not need it.

Configure with a JSON array in the environment:

    MCP_SERVERS='[{"name":"linear","command":"npx","args":["-y","@linear/mcp-server"],
                   "env":{"LINEAR_API_KEY":"..."}}]'
"""
from __future__ import annotations

import json
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from .base import Tool, ToolContext, ToolResult


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]

    @classmethod
    def parse_all(cls, raw: str) -> List["MCPServerConfig"]:
        try:
            entries = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            app_logger.error("MCP_SERVERS is not valid JSON; ignoring", error=str(exc))
            return []
        if not isinstance(entries, list):
            app_logger.error("MCP_SERVERS must be a JSON array; ignoring")
            return []

        configs: List[MCPServerConfig] = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("command"):
                app_logger.warning("Skipping MCP server entry without a `command`", entry=str(entry)[:120])
                continue
            configs.append(
                cls(
                    name=str(entry.get("name") or entry["command"]),
                    command=str(entry["command"]),
                    args=[str(arg) for arg in entry.get("args") or []],
                    env={str(k): str(v) for k, v in (entry.get("env") or {}).items()},
                )
            )
        return configs


def _flatten_content(content: Any) -> str:
    """Render an MCP tool result's content blocks as plain text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)

    parts: List[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
            continue
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
            continue
        resource = getattr(block, "resource", None)
        if resource is not None:
            parts.append(str(getattr(resource, "text", resource)))
            continue
        parts.append(str(block))
    return "\n".join(part for part in parts if part).strip()


class MCPBridge:
    """Connects to configured MCP servers and adapts their tools."""

    def __init__(self, configs: Optional[List[MCPServerConfig]] = None):
        self.configs = configs if configs is not None else MCPServerConfig.parse_all(settings.MCP_SERVERS)
        self._stack: Optional[AsyncExitStack] = None
        self._sessions: Dict[str, Any] = {}
        self.tools: List[Tool] = []

    @property
    def enabled(self) -> bool:
        if not self.configs:
            return False
        if settings.is_serverless:
            app_logger.info("MCP servers configured but skipped: serverless cannot spawn stdio subprocesses")
            return False
        return True

    async def __aenter__(self) -> "MCPBridge":
        if not self.enabled:
            return self

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            app_logger.warning(
                "MCP_SERVERS is set but the `mcp` package is not installed. "
                "Install it with: pip install -r backend/requirements-dev.txt"
            )
            return self

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        for config in self.configs:
            try:
                transport = await self._stack.enter_async_context(
                    stdio_client(
                        StdioServerParameters(
                            command=config.command,
                            args=config.args,
                            env=config.env or None,
                        )
                    )
                )
                session = await self._stack.enter_async_context(ClientSession(*transport))
                await session.initialize()
                self._sessions[config.name] = session

                listed = await session.list_tools()
                for descriptor in listed.tools:
                    self.tools.append(self._adapt(config.name, session, descriptor))

                app_logger.info(
                    "Connected to MCP server",
                    server=config.name,
                    tools=[d.name for d in listed.tools],
                )
            except Exception as exc:
                # One unreachable server must not prevent the pipeline running
                # with its built-in tools.
                app_logger.error(
                    "Could not connect to MCP server; continuing without it",
                    server=config.name,
                    error=str(exc)[:300],
                )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._stack is not None:
            await self._stack.__aexit__(*exc)
            self._stack = None
        self._sessions.clear()
        self.tools = []

    @staticmethod
    def _adapt(server_name: str, session: Any, descriptor: Any) -> Tool:
        """Wrap one remote MCP tool as a local `Tool`."""
        qualified = f"mcp__{server_name}__{descriptor.name}"
        schema = getattr(descriptor, "inputSchema", None) or {"type": "object", "properties": {}}

        async def handler(arguments: Dict[str, Any], _ctx: ToolContext) -> ToolResult:
            try:
                response = await session.call_tool(descriptor.name, arguments)
            except Exception as exc:
                return ToolResult.error(f"MCP server '{server_name}' failed: {str(exc)[:200]}")

            text = _flatten_content(getattr(response, "content", response))
            if getattr(response, "isError", False):
                return ToolResult.error(text or "MCP tool reported an error")
            return ToolResult(content=text or "(no content returned)", data={"server": server_name})

        return Tool(
            name=qualified,
            description=(
                f"[via MCP server '{server_name}'] "
                f"{getattr(descriptor, 'description', '') or descriptor.name}"
            ),
            parameters=schema,
            handler=handler,
        )
