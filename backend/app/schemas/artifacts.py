"""
Strict artifact schemas produced by the agent pipeline.

Each agent's output is validated against one of these models. Validation errors
are fed back to the model as a repair prompt, so the field descriptions here
double as the specification the model sees -- keep them precise.

Coercion is deliberately forgiving where models are unreliable (numbers written
as "4 hours", stray nested objects in tech_stack) and strict where correctness
matters (RICE inputs, non-empty lists).
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator


def _as_text(value: Any) -> Any:
    """Flatten a structured value into prose.

    Models frequently return a richer shape than a plain string where the
    instruction implies structure -- asking for "Given/When/Then acceptance
    criteria" reliably produces `{"given": ..., "when": ..., "then": ...}`
    objects. That is a fair reading of the request, so the schema absorbs it
    instead of burning repair attempts insisting on a flat string.
    """
    if isinstance(value, str) or value is None:
        return value

    if isinstance(value, dict):
        lowered = {str(key).lower(): item for key, item in value.items()}
        if {"given", "when", "then"} <= set(lowered):
            return (
                f"Given {lowered['given']}, when {lowered['when']}, then {lowered['then']}"
            )
        for key in ("criterion", "criteria", "statement", "text", "description", "value", "name", "title"):
            candidate = lowered.get(key)
            if isinstance(candidate, (str, int, float)):
                return str(candidate)
        return "; ".join(f"{key}: {_as_text(item)}" for key, item in value.items())

    if isinstance(value, (list, tuple)):
        return " ".join(str(_as_text(item)) for item in value)

    return str(value)


#: A string field that tolerates the model returning an object or list instead.
Text = Annotated[str, BeforeValidator(_as_text)]


def _as_list(value: Any) -> Any:
    """Wrap a bare scalar into a single-item list.

    A field asking for "acceptance criteria" is a list even when there happens
    to be exactly one -- but a model reasons about "the acceptance criterion"
    for a simple story and writes a bare string instead of `[...]`. Rejecting
    that costs a full repair round to fix what one `[value]` wrap resolves for
    free, and it was the single largest cause of failed PRD generations. A
    genuinely absent field is left alone: `None`/missing should still fail the
    length-minimum check that follows, since a thin list is a real quality
    problem this coercion is not meant to paper over.
    """
    if value is None or isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


#: A list-of-Text field that tolerates the model returning a bare scalar.
TextList = Annotated[List[Text], BeforeValidator(_as_list)]


class Artifact(BaseModel):
    """Base for every agent output: ignore unknown keys, trim whitespace."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def _cap_oversized_lists(cls, data: Any) -> Any:
        """Truncate lists that exceed their declared maximum.

        Asked for "at most 8 target users", models routinely return ten good
        ones. Rejecting the whole artifact over that costs a full repair round --
        roughly doubling the tokens for the agent -- to discard the same two
        entries truncation drops for free. Minimums still fail loudly, because a
        response that is too *thin* is a real quality problem rather than an
        excess of enthusiasm.
        """
        if not isinstance(data, dict):
            return data

        for name, field in cls.model_fields.items():
            value = data.get(name)
            if not isinstance(value, list):
                continue
            for constraint in field.metadata:
                limit = getattr(constraint, "max_length", None)
                if isinstance(limit, int) and len(value) > limit:
                    data[name] = value[:limit]
                    break
        return data


def _first_number(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else default


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #


class JobToBeDone(Artifact):
    situation: str = Field(..., description="The triggering context: 'When I am ...'")
    motivation: str = Field(..., description="What the user wants to do")
    outcome: str = Field(..., description="The progress the user is trying to make")


class ProductVision(Artifact):
    product_name: str = Field(..., min_length=2, max_length=120)
    problem_statement: Text = Field(..., min_length=40, description="The problem, stated without naming a solution")
    value_proposition: Text = Field(..., min_length=20, description="One sentence on why this wins")
    target_users: TextList = Field(..., min_length=1, max_length=8)
    core_goals: TextList = Field(..., min_length=1, max_length=8)
    key_features_high_level: TextList = Field(..., min_length=2, max_length=12)
    non_goals: TextList = Field(default_factory=list, max_length=8, description="Explicitly out of scope for v1")
    jobs_to_be_done: List[JobToBeDone] = Field(default_factory=list, max_length=6)
    assumptions: TextList = Field(default_factory=list, max_length=8, description="Beliefs that would invalidate the plan if wrong")


# --------------------------------------------------------------------------- #
# Analyst (PRD)
# --------------------------------------------------------------------------- #


class UserPersona(Artifact):
    name: str = Field(..., description="Role-based name, e.g. 'Priya, Ops Lead'")
    description: str
    pain_points: TextList = Field(..., min_length=1, max_length=6)
    current_workaround: Optional[str] = Field(None, description="What they do today instead")


class UserStory(Artifact):
    title: str
    as_a: str
    i_want_to: str
    so_that: str
    acceptance_criteria: TextList = Field(
        default_factory=list,
        max_length=8,
        description="Falsifiable Given/When/Then statements",
    )


class SuccessMetric(Artifact):
    name: str
    description: str
    target: str = Field(..., description="Baseline -> target within a timeframe, e.g. '12% -> 20% in 2 quarters'")
    metric_type: str = Field(default="leading", description="'leading', 'lagging', or 'guardrail'")

    @field_validator("metric_type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        text = str(value or "leading").strip().lower()
        return text if text in {"leading", "lagging", "guardrail"} else "leading"


class PRD(Artifact):
    problem_statement: Text = Field(..., min_length=40)
    target_users: TextList = Field(..., min_length=1, max_length=8)
    non_goals: TextList = Field(default_factory=list, max_length=8)
    user_personas: List[UserPersona] = Field(..., min_length=1, max_length=4)
    user_stories: List[UserStory] = Field(..., min_length=3, max_length=15)
    success_metrics: List[SuccessMetric] = Field(..., min_length=2, max_length=8)
    risks: TextList = Field(default_factory=list, max_length=8)
    open_questions: TextList = Field(default_factory=list, max_length=8)


# --------------------------------------------------------------------------- #
# Prioritizer (RICE)
# --------------------------------------------------------------------------- #


class RiceInputs(Artifact):
    """RICE estimates. The score is computed in Python, never by the model."""

    reach: float = Field(..., ge=0, description="Users affected per quarter")
    impact: float = Field(..., ge=0.25, le=3.0, description="One of 3, 2, 1, 0.5, 0.25")
    confidence: float = Field(..., ge=10, le=100, description="Percentage: 100 high, 80 medium, 50 low")
    effort: float = Field(..., gt=0, le=60, description="Person-months")
    score: float = Field(default=0.0, description="Computed: (reach * impact * confidence/100) / effort")

    @field_validator("reach", "impact", "confidence", "effort", "score", mode="before")
    @classmethod
    def _coerce(cls, value: Any) -> float:
        return _first_number(value, 0.0)

    def compute_score(self) -> float:
        return round((self.reach * self.impact * (self.confidence / 100.0)) / self.effort, 1)


class ScoredFeature(Artifact):
    name: str
    description: str
    rice: RiceInputs
    justification: Text = Field(..., description="Why these estimates, in 1-2 lines")
    moscow: str = Field(default="Should", description="Must, Should, Could, or Won't")

    @field_validator("moscow", mode="before")
    @classmethod
    def _normalize_moscow(cls, value: Any) -> str:
        text = str(value or "Should").strip().lower().replace("-", "").replace("'", "")
        mapping = {"must": "Must", "should": "Should", "could": "Could", "wont": "Won't", "will not": "Won't"}
        for key, label in mapping.items():
            if text.startswith(key):
                return label
        return "Should"


class FeaturePriorities(Artifact):
    features_detailed: List[ScoredFeature] = Field(..., min_length=2, max_length=12)
    sequencing_rationale: Text = Field(..., description="Why this order, referencing dependencies and risk")


# --------------------------------------------------------------------------- #
# Architect
# --------------------------------------------------------------------------- #


class ApiEndpoint(Artifact):
    name: str
    method: str = Field(default="GET")
    endpoint: str
    description: str

    @field_validator("method", mode="before")
    @classmethod
    def _upper(cls, value: Any) -> str:
        method = str(value or "GET").strip().upper()
        return method if method in {"GET", "POST", "PUT", "PATCH", "DELETE"} else "GET"


class SchemaField(Artifact):
    name: str
    type: str
    constraints: str = ""


class DatabaseTable(Artifact):
    table_name: str
    fields: List[SchemaField] = Field(..., min_length=1)


class ArchitectureDecision(Artifact):
    decision: str
    rationale: str
    alternatives_considered: TextList = Field(default_factory=list, max_length=4)
    tradeoffs: str = ""


class SystemArchitecture(Artifact):
    system_design: Text = Field(..., min_length=40, description="The shape of the system in prose")
    architecture_pattern: str = Field(
        default="modular monolith",
        description="e.g. modular monolith, microservices, serverless, event-driven",
    )
    tech_stack: Dict[str, str] = Field(..., min_length=1)
    architecture_components: TextList = Field(..., min_length=2, max_length=15)
    api_endpoints: List[ApiEndpoint] = Field(..., min_length=2, max_length=20)
    database_schema: List[DatabaseTable] = Field(..., min_length=1, max_length=12)
    non_functional_requirements: TextList = Field(default_factory=list, max_length=8)
    key_decisions: List[ArchitectureDecision] = Field(default_factory=list, max_length=6)

    @field_validator("tech_stack", mode="before")
    @classmethod
    def _flatten_stack(cls, value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {"stack": str(value)}
        flattened: Dict[str, str] = {}
        for key, item in value.items():
            if isinstance(item, (list, tuple)):
                flattened[str(key)] = ", ".join(str(entry) for entry in item)
            elif isinstance(item, dict):
                flattened[str(key)] = ", ".join(f"{k}: {v}" for k, v in item.items())
            else:
                flattened[str(key)] = str(item)
        return flattened


# --------------------------------------------------------------------------- #
# Ticket generator
# --------------------------------------------------------------------------- #


class Task(Artifact):
    title: str
    description: str = ""
    estimated_hours: float = Field(default=4.0, ge=0.5, le=120)

    @field_validator("estimated_hours", mode="before")
    @classmethod
    def _coerce_hours(cls, value: Any) -> float:
        return max(0.5, min(120.0, _first_number(value, 4.0)))


class Story(Artifact):
    story_title: str
    description: str = ""
    acceptance_criteria: TextList = Field(..., min_length=1, max_length=8)
    tasks: List[Task] = Field(..., min_length=1, max_length=8)
    story_points: int = Field(default=3, ge=1, le=21)

    @field_validator("story_points", mode="before")
    @classmethod
    def _fibonacci(cls, value: Any) -> int:
        raw = _first_number(value, 3.0)
        return min({1, 2, 3, 5, 8, 13, 21}, key=lambda point: abs(point - raw))


class Epic(Artifact):
    epic_name: str
    description: str = ""
    priority: str = Field(default="Medium")
    stories: List[Story] = Field(..., min_length=1, max_length=8)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: Any) -> str:
        text = str(value or "Medium").strip().capitalize()
        return text if text in {"High", "Medium", "Low"} else "Medium"


class Tickets(Artifact):
    epics: List[Epic] = Field(..., min_length=1, max_length=8)
    delivery_sequence: TextList = Field(
        default_factory=list,
        max_length=8,
        description="Epic names in build order, walking skeleton first",
    )


# --------------------------------------------------------------------------- #
# Critic
# --------------------------------------------------------------------------- #


class ArtifactCritique(Artifact):
    artifact: str = Field(..., description="One of: plan, prd, architecture, tickets, features_detailed")
    completeness: float = Field(..., ge=0, le=10)
    consistency: float = Field(..., ge=0, le=10)
    specificity: float = Field(..., ge=0, le=10)
    feasibility: float = Field(..., ge=0, le=10)
    issues: TextList = Field(default_factory=list, max_length=6)
    fix_instructions: TextList = Field(
        default_factory=list,
        max_length=6,
        description="Imperative, actionable edits for the regenerating agent",
    )

    @field_validator("completeness", "consistency", "specificity", "feasibility", mode="before")
    @classmethod
    def _coerce_score(cls, value: Any) -> float:
        return max(0.0, min(10.0, _first_number(value, 5.0)))

    @property
    def overall(self) -> float:
        return round((self.completeness + self.consistency + self.specificity + self.feasibility) / 4, 2)


class Critique(Artifact):
    critiques: List[ArtifactCritique] = Field(..., min_length=1, max_length=5)
    overall_assessment: Text
    blocking_issues: TextList = Field(default_factory=list, max_length=6)

    @property
    def overall_quality(self) -> float:
        if not self.critiques:
            return 0.0
        return round(sum(item.overall for item in self.critiques) / len(self.critiques), 2)

    def failing(self, threshold: float) -> List[str]:
        """Artifact names scoring below the acceptance threshold."""
        return [item.artifact for item in self.critiques if item.overall < threshold]


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


class Citation(Artifact):
    marker: str = Field(..., description="In-text marker, e.g. 'S1'")
    doc_id: str
    title: str
    heading: str = ""
    score: float = 0.0


class AgentStep(Artifact):
    """One node in the executed graph, surfaced to the UI as a live trace."""

    agent: str
    label: str
    status: str = "completed"
    model: str = ""
    duration_seconds: float = 0.0
    tool_calls: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    tokens: int = 0
    repairs: int = 0
    note: str = ""
