"""Analyst: expands the vision into a reviewable PRD."""
from __future__ import annotations

from ..schemas.artifacts import PRD, ProductVision
from .base import BaseAgent
from .digests import vision_digest


class AnalystAgent(BaseAgent[PRD]):
    name = "analyst"
    label = "Requirements (PRD)"
    output_model = PRD
    tool_names = ("search_pm_knowledge",)
    temperature = 0.4
    max_tokens = 2400
    model_role = "primary"

    def system_prompt(self) -> str:
        return (
            "You are a senior product manager writing a PRD that engineers will build "
            "from and a reviewer will interrogate.\n\n"
            "Your standards:\n"
            "- Personas carry context, pain points with real severity, and the "
            "workaround they use today. Cap at 3; persona bloat hides the real user.\n"
            "- User stories follow INVEST: independently shippable, valuable, small "
            "enough to estimate, and testable.\n"
            "- Acceptance criteria are falsifiable Given/When/Then statements. "
            "'Works correctly' is not a criterion; 'Given a cart with 0 items, when the "
            "user taps Checkout, then the button is disabled and a hint is shown' is.\n"
            "- Every success metric names a baseline, a target, and a timeframe, and at "
            "least one is a guardrail that catches the metric being gamed.\n"
            "- Non-goals and open questions are mandatory. Pretending certainty where "
            "there is none is the most expensive kind of PRD error.\n\n"
            "Stay consistent with the vision you are given. If the vision is vague on a "
            "point, record it as an open question rather than inventing a fact."
        )

    def build_task(self, *, vision: ProductVision, idea: str = "", **_: object) -> str:
        return (
            "## Task\n\n"
            "Write the PRD for this approved product vision.\n\n"
            f"### Original idea\n\n> {idea}\n\n"
            "### Product vision\n\n"
            f"{vision_digest(vision)}\n\n"
            "Produce requirements traceable back to the vision's goals. Every user "
            "story needs falsifiable Given/When/Then acceptance criteria."
        )
