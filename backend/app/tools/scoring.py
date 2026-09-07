"""
Deterministic prioritization scoring.

The model supplies the *estimates* (reach, impact, confidence, effort) and the
justification; Python does the arithmetic and the ranking. Letting an LLM
compute and sort RICE scores invites silent arithmetic errors and, worse,
invented numbers that look authoritative.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Tool, ToolContext, ToolResult

IMPACT_SCALE = {3.0: "massive", 2.0: "high", 1.0: "medium", 0.5: "low", 0.25: "minimal"}


def _snap_impact(value: float) -> float:
    """Snap a free-form impact estimate onto the canonical RICE scale."""
    return min(IMPACT_SCALE, key=lambda allowed: abs(allowed - value))


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_rice(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score and rank features. Pure function -- also used by the MCP server."""
    scored: List[Dict[str, Any]] = []

    for feature in features:
        name = str(feature.get("name") or "").strip()
        if not name:
            continue

        reach = max(0.0, _number(feature.get("reach"), 1000))
        impact = _snap_impact(max(0.25, min(3.0, _number(feature.get("impact"), 1.0))))
        confidence = max(10.0, min(100.0, _number(feature.get("confidence"), 70)))
        effort = max(0.1, min(60.0, _number(feature.get("effort"), 2.0)))
        score = round((reach * impact * (confidence / 100.0)) / effort, 1)

        scored.append(
            {
                "name": name,
                "description": str(feature.get("description") or ""),
                "justification": str(feature.get("justification") or ""),
                "rice": {
                    "reach": round(reach, 1),
                    "impact": impact,
                    "confidence": round(confidence, 1),
                    "effort": round(effort, 2),
                    "score": score,
                },
            }
        )

    scored.sort(key=lambda item: item["rice"]["score"], reverse=True)
    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank
    return scored


async def _score(args: Dict[str, Any], _ctx: ToolContext) -> ToolResult:
    features = args.get("features")
    if not isinstance(features, list) or not features:
        return ToolResult.error("`features` must be a non-empty array")

    scored = compute_rice(features)
    if not scored:
        return ToolResult.error("No features had a usable `name`")

    lines = ["Ranked by RICE = (reach x impact x confidence/100) / effort:", ""]
    for item in scored:
        rice = item["rice"]
        lines.append(
            f"{item['rank']}. {item['name']} — score {rice['score']} "
            f"(reach {rice['reach']:g}, impact {rice['impact']:g} "
            f"[{IMPACT_SCALE[rice['impact']]}], confidence {rice['confidence']:g}%, "
            f"effort {rice['effort']:g} person-months)"
        )

    return ToolResult(content="\n".join(lines), data={"features_detailed": scored})


score_features_rice = Tool(
    name="score_features_rice",
    description=(
        "Compute exact RICE scores and rank features. Supply your own estimates "
        "for reach (users per quarter), impact (3=massive, 2=high, 1=medium, "
        "0.5=low, 0.25=minimal), confidence (10-100%), and effort (person-months). "
        "This tool performs the arithmetic and sorting -- never calculate RICE "
        "scores yourself."
    ),
    parameters={
        "type": "object",
        "properties": {
            "features": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "reach": {"type": "number", "description": "Users affected per quarter"},
                        "impact": {"type": "number", "enum": [0.25, 0.5, 1, 2, 3]},
                        "confidence": {"type": "number", "minimum": 10, "maximum": 100},
                        "effort": {"type": "number", "description": "Person-months", "exclusiveMinimum": 0},
                        "justification": {"type": "string", "description": "Why these estimates"},
                    },
                    "required": ["name", "reach", "impact", "confidence", "effort"],
                },
            }
        },
        "required": ["features"],
    },
    handler=_score,
)
