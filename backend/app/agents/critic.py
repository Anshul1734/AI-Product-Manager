"""
Critic: adversarial review of the assembled plan.

Runs on the fast model with no tools. Its job is to find defects and write
imperative fix instructions that the refine pass hands back to the originating
agent -- it never rewrites artifacts itself, which keeps review and authorship
separate.
"""
from __future__ import annotations

from typing import Dict

from ..schemas.artifacts import Critique
from .base import BaseAgent


class CriticAgent(BaseAgent[Critique]):
    name = "critic"
    label = "Quality review"
    output_model = Critique
    tool_names = ()
    temperature = 0.2
    max_tokens = 1800
    # A different model family from the authors, so the review is not just the
    # same model agreeing with itself -- and it draws on its own TPM bucket.
    model_role = "alt"

    def system_prompt(self) -> str:
        return (
            "You are a demanding reviewer auditing a product plan before it goes to an "
            "engineering team. You do not rewrite it; you find what is wrong with it.\n\n"
            "Score each artifact 0-10 on four axes:\n"
            "- completeness: are required fields present and substantive?\n"
            "- consistency: do the artifacts agree with each other and the original idea? "
            "Contradictions between the PRD's users and the vision's users, or endpoints "
            "with no story behind them, are consistency failures.\n"
            "- specificity: is it specific to this product, or generic filler that would "
            "fit any product? Generic content scores below 5.\n"
            "- feasibility: could the described team actually build this, and do the "
            "estimates and metrics survive scrutiny?\n\n"
            "Calibration: 9-10 is exceptional and rare. 7-8 is solid, ships as-is. 5-6 "
            "has real gaps. Below 5 needs rework. Do not inflate; a review that scores "
            "everything 8 is useless.\n\n"
            "For any artifact below 7, write fix_instructions as direct imperatives "
            "aimed at whoever regenerates it: 'Replace the 40% adoption target with a "
            "baseline and timeframe', not 'metrics could be better'. Every instruction "
            "must be actionable without further clarification.\n\n"
            "List blocking_issues only for defects that make the plan unsafe to build "
            "from, such as a security requirement that is missing entirely."
        )

    def build_task(self, *, idea: str, bundle: Dict[str, str], **_: object) -> str:
        sections = [
            "## Task\n\nReview this generated plan against the original request.",
            f"### Original idea\n\n> {idea}",
        ]
        for artifact, digest in bundle.items():
            sections.append(f"### Artifact: {artifact}\n\n{digest}")
        sections.append(
            "Produce exactly one critique entry per artifact shown above, using the "
            "same artifact names."
        )
        return "\n\n".join(sections)
