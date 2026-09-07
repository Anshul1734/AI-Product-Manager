"""
Structured-output helpers: compact schema rendering, tolerant JSON extraction,
and validation errors formatted for a repair prompt.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_NOISE_KEYS = {"title", "additionalProperties", "$defs", "definitions"}
_MAX_INLINE_DEPTH = 6


def _inline_refs(node: Any, defs: Dict[str, Any], depth: int = 0) -> Any:
    """Resolve $ref pointers inline and strip schema noise.

    Pydantic emits `$defs` plus `$ref` pointers. Models follow a single flat
    shape far more reliably than one they have to assemble from references, so
    the schema handed to the model is fully inlined.
    """
    if depth > _MAX_INLINE_DEPTH:
        return {"type": "object"}

    if isinstance(node, dict):
        if "$ref" in node:
            ref_name = str(node["$ref"]).rsplit("/", 1)[-1]
            target = defs.get(ref_name)
            return _inline_refs(target, defs, depth + 1) if target else {"type": "object"}

        cleaned: Dict[str, Any] = {}
        for key, value in node.items():
            if key in _NOISE_KEYS:
                continue
            if key == "anyOf" and isinstance(value, list):
                # Optional[X] renders as anyOf[X, null]; collapse to X.
                non_null = [item for item in value if item.get("type") != "null"]
                if len(non_null) == 1:
                    inlined = _inline_refs(non_null[0], defs, depth + 1)
                    if isinstance(inlined, dict):
                        cleaned.update(inlined)
                        continue
            cleaned[key] = _inline_refs(value, defs, depth + 1)
        return cleaned

    if isinstance(node, list):
        return [_inline_refs(item, defs, depth + 1) for item in node]

    return node


def render_schema(model: Type[BaseModel]) -> str:
    """Render a Pydantic model as a compact, self-contained JSON schema."""
    raw = model.model_json_schema()
    defs = raw.get("$defs") or raw.get("definitions") or {}
    return json.dumps(_inline_refs(raw, defs), indent=2)


def extract_json_object(text: str) -> Dict[str, Any]:
    """Parse a JSON object from a model response.

    JSON mode usually returns clean JSON, but fenced blocks and leading prose
    still appear often enough to be worth handling.
    """
    candidate = (text or "").strip()
    if not candidate:
        raise ValueError("Model returned an empty response")

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    start = candidate.find("{")
    if start == -1:
        raise ValueError("Response contained no JSON object")

    end = candidate.rfind("}")
    if end > start:
        blob = candidate[start : end + 1]
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            # Trailing commas are the most common single defect.
            repaired = re.sub(r",\s*([}\]])", r"\1", blob)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # Last resort: the response was cut off mid-object (hit the token ceiling).
    # Salvaging it beats discarding a mostly-complete artifact, and any field
    # lost to truncation surfaces as a normal validation error afterwards.
    salvaged = _close_truncated_json(candidate[start:])
    if salvaged is not None:
        return salvaged

    raise ValueError("Response was not valid JSON and could not be repaired")


def _close_truncated_json(blob: str) -> Optional[Dict[str, Any]]:
    """Balance a truncated JSON object by closing its open structures."""
    depth_stack: List[str] = []
    in_string = False
    escaped = False
    last_safe: Optional[int] = None

    for index, char in enumerate(blob):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in "{[":
            depth_stack.append("}" if char == "{" else "]")
        elif char in "}]":
            if depth_stack:
                depth_stack.pop()
            if not depth_stack:
                last_safe = index
        elif char == "," and len(depth_stack) == 1:
            # A top-level comma marks a complete key/value pair boundary.
            last_safe = index - 1

    for cut in (len(blob) - 1, last_safe):
        if cut is None:
            continue
        prefix = blob[: cut + 1].rstrip().rstrip(",")
        stack: List[str] = []
        in_str = False
        esc = False
        for char in prefix:
            if esc:
                esc = False
                continue
            if char == "\\" and in_str:
                esc = True
                continue
            if char == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if char in "{[":
                stack.append("}" if char == "{" else "]")
            elif char in "}]" and stack:
                stack.pop()
        attempt = prefix + ('"' if in_str else "") + "".join(reversed(stack))
        try:
            parsed = json.loads(re.sub(r",\s*([}\]])", r"\1", attempt))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def format_validation_errors(error: ValidationError, limit: int = 12) -> str:
    """Turn a ValidationError into an actionable, model-readable checklist."""
    lines: List[str] = []
    for detail in error.errors()[:limit]:
        location = ".".join(str(part) for part in detail.get("loc", ())) or "(root)"
        lines.append(f"- `{location}`: {detail.get('msg', 'invalid value')}")
    remaining = len(error.errors()) - limit
    if remaining > 0:
        lines.append(f"- …and {remaining} more problem(s)")
    return "\n".join(lines)
