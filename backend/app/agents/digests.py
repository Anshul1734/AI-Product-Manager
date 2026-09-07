"""
Compact renderings of upstream artifacts for downstream prompts.

Passing `model_dump_json()` between agents is the obvious approach and the wrong
one: a full PRD serializes to roughly 3,000 tokens of punctuation-heavy JSON,
which on a metered account is most of a per-minute budget spent restating
structure the next agent does not need. These digests carry the same decisions
in about a sixth of the tokens, and read more naturally besides.

Each digest keeps what the *consumer* needs. The architect needs the problem,
users, and story intent; it does not need every acceptance criterion. The ticket
generator needs endpoint paths and table names; it does not need the rationale
behind each architectural decision.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ..schemas.artifacts import (
    PRD,
    FeaturePriorities,
    ProductVision,
    ScoredFeature,
    SystemArchitecture,
    Tickets,
)


def _lines(label: str, items: Sequence[Any], limit: int = 8) -> List[str]:
    if not items:
        return []
    shown = [str(item) for item in items[:limit]]
    out = [f"{label}:"]
    out += [f"  - {item}" for item in shown]
    if len(items) > limit:
        out.append(f"  - (+{len(items) - limit} more)")
    return out


def vision_digest(vision: ProductVision) -> str:
    out = [
        f"Product: {vision.product_name}",
        f"Problem: {vision.problem_statement}",
        f"Value: {vision.value_proposition}",
    ]
    out += _lines("Target users", vision.target_users, 6)
    out += _lines("Goals", vision.core_goals, 6)
    out += _lines("Candidate features", vision.key_features_high_level, 12)
    out += _lines("Non-goals", vision.non_goals, 5)
    if vision.jobs_to_be_done:
        out.append("Jobs to be done:")
        for job in vision.jobs_to_be_done[:4]:
            out.append(f"  - When {job.situation}, wants to {job.motivation}, so that {job.outcome}")
    out += _lines("Assumptions", vision.assumptions, 4)
    return "\n".join(out)


def prd_digest(prd: PRD, *, include_criteria: bool = False) -> str:
    out = [f"Problem: {prd.problem_statement}"]
    out += _lines("Target users", prd.target_users, 6)
    out += _lines("Non-goals", prd.non_goals, 5)

    if prd.user_personas:
        out.append("Personas:")
        for persona in prd.user_personas:
            pains = "; ".join(persona.pain_points[:3])
            out.append(f"  - {persona.name}: {pains}")

    if prd.user_stories:
        out.append("User stories:")
        for story in prd.user_stories:
            out.append(f"  - {story.title}: as {story.as_a}, wants to {story.i_want_to} so that {story.so_that}")
            if include_criteria and story.acceptance_criteria:
                for criterion in story.acceptance_criteria[:2]:
                    out.append(f"      AC: {criterion}")

    if prd.success_metrics:
        out.append("Success metrics:")
        for metric in prd.success_metrics:
            out.append(f"  - {metric.name} ({metric.metric_type}): target {metric.target}")

    out += _lines("Risks", prd.risks, 4)
    return "\n".join(out)


def features_digest(features: Optional[Sequence[ScoredFeature]], limit: int = 10) -> str:
    if not features:
        return ""
    out = ["Prioritized features (RICE score, MoSCoW):"]
    for index, feature in enumerate(features[:limit], start=1):
        out.append(f"  {index}. {feature.name} — {feature.rice.score} ({feature.moscow})")
    return "\n".join(out)


def architecture_digest(architecture: SystemArchitecture) -> str:
    out = [
        f"Pattern: {architecture.architecture_pattern}",
        f"Design: {architecture.system_design}",
        "Stack: " + ", ".join(f"{layer}={choice}" for layer, choice in architecture.tech_stack.items()),
    ]
    out += _lines("Components", architecture.architecture_components, 10)

    if architecture.api_endpoints:
        out.append("Endpoints:")
        for endpoint in architecture.api_endpoints[:14]:
            out.append(f"  - {endpoint.method} {endpoint.endpoint} — {endpoint.description}")

    if architecture.database_schema:
        out.append("Tables:")
        for table in architecture.database_schema[:10]:
            fields = ", ".join(field.name for field in table.fields[:8])
            out.append(f"  - {table.table_name}({fields})")

    out += _lines("Non-functional requirements", architecture.non_functional_requirements, 5)
    return "\n".join(out)


def tickets_digest(tickets: Tickets) -> str:
    out = ["Backlog:"]
    for epic in tickets.epics:
        points = sum(story.story_points for story in epic.stories)
        out.append(f"  - Epic '{epic.epic_name}' [{epic.priority}] — {len(epic.stories)} stories, {points} pts")
        for story in epic.stories[:4]:
            out.append(
                f"      * {story.story_title} ({story.story_points} pts, "
                f"{len(story.acceptance_criteria)} AC, {len(story.tasks)} tasks)"
            )
    if tickets.delivery_sequence:
        out.append("Delivery order: " + " -> ".join(tickets.delivery_sequence))
    return "\n".join(out)


def review_digest(
    vision: Optional[ProductVision],
    prd: Optional[PRD],
    priorities: Optional[FeaturePriorities],
    architecture: Optional[SystemArchitecture],
    tickets: Optional[Tickets],
) -> Dict[str, str]:
    """Per-artifact digests for the critic.

    The critic needs enough substance to judge specificity and cross-artifact
    consistency, but feeding it every field would cost more tokens than
    generating the plan did.
    """
    bundle: Dict[str, str] = {}
    if vision:
        bundle["plan"] = vision_digest(vision)
    if prd:
        bundle["prd"] = prd_digest(prd, include_criteria=True)
    if priorities:
        bundle["features_detailed"] = "\n".join(
            [
                features_digest(priorities.features_detailed, limit=12),
                f"Sequencing rationale: {priorities.sequencing_rationale}",
            ]
        )
    if architecture:
        bundle["architecture"] = architecture_digest(architecture)
    if tickets:
        bundle["tickets"] = tickets_digest(tickets)
    return bundle
