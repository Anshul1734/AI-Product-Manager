"""
Tool primitives.

A tool is a JSON-schema-described async callable that the model can invoke
through native function calling. Tools return a string for the model plus
optional structured data and citations for the pipeline, so retrieval
provenance survives all the way to the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..schemas.artifacts import Citation


@dataclass
class ToolResult:
    content: str
    citations: List[Citation] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    ok: bool = True

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(content=f"ERROR: {message}", ok=False)


@dataclass
class ToolContext:
    """Per-run dependencies handed to tool implementations."""

    retriever: Optional[Any] = None
    memory: Optional[Any] = None
    thread_id: Optional[str] = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any], ToolContext], Awaitable[ToolResult]]

    def schema(self) -> Dict[str, Any]:
        """OpenAI/Groq function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
