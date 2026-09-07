"""Planner: turns a raw idea into a defensible product vision."""
from __future__ import annotations

from ..schemas.artifacts import ProductVision
from .base import BaseAgent


class PlannerAgent(BaseAgent[ProductVision]):
    name = "planner"
    label = "Product vision"
    output_model = ProductVision
    tool_names = ("search_pm_knowledge", "recall_similar_plans")
    temperature = 0.5
    max_tokens = 1700
    model_role = "primary"

    def system_prompt(self) -> str:
        return (
            "You are a principal product manager framing a new product bet.\n\n"
            "Your standards:\n"
            "- State the problem without smuggling in the solution. 'Users have no "
            "dashboard' is a missing feature; 'operators cannot tell which shipments "
            "will miss SLA until customers complain' is a problem.\n"
            "- Name target users by role and context, never as 'everyone' or 'users'.\n"
            "- Goals must be outcomes you could later measure, not activities.\n"
            "- Declare non-goals. A vision that excludes nothing has not made a choice.\n"
            "- Surface the assumptions that would sink the plan if they turned out "
            "false, so they can be tested early.\n"
            "- Write jobs-to-be-done in the situation/motivation/outcome form.\n\n"
            "Be specific to the idea you are given. Reject the temptation to describe "
            "a generic SaaS product."
        )

    def build_task(self, *, idea: str, **_: object) -> str:
        return (
            "## Task\n\n"
            "Frame the product vision for this idea:\n\n"
            f"> {idea}\n\n"
            "Check whether similar plans already exist so you can stay consistent with "
            "prior terminology and avoid repeating a framing that scored poorly."
        )
